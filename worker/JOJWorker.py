from bs4 import BeautifulSoup
from util import Logger, getProjRepoName
import multiprocessing
import requests
import zipfile
import time
import os


class JOJWorker():
    def __init__(self, args, courseID, sid, hgroups, logger=Logger()):
        def createSess(cookies):
            s = requests.Session()
            s.cookies.update(cookies)
            return s

        cookies = {
            'JSESSIONID': 'dummy',
            'save': '1',
            'sid': sid,
        }
        self.args = args
        self.sess = createSess(cookies=cookies)
        self.courseID = courseID
        self.hgroups = hgroups
        self.logger = logger

    def uploadZip(self, homeworkID, problemID, zipPath, lang):
        files = {
            'code': ('code.zip', open(zipPath, 'rb'), 'application/zip'),
        }
        postUrl = f'https://joj.sjtu.edu.cn/d/{self.courseID}/homework/{homeworkID}/{problemID}/submit'
        html = self.sess.get(postUrl).text
        soup = BeautifulSoup(html, features="lxml")
        csrfToken = soup.select(
            "#panel > div.main > div > div.medium-9.columns > div:nth-child(2) > div.section__body > form > div:nth-child(3) > div > input[type=hidden]:nth-child(1)"
        )[0].get('value')
        response = self.sess.post(
            postUrl,
            files=files,
            data={
                'csrf_token': csrfToken,
                'lang': lang
            },
        )
        return response

    def getProblemStatus(self, url):
        soup = None
        while True:
            html = self.sess.get(url).text
            soup = BeautifulSoup(html, features="lxml")
            status = soup.select(
                "#status > div.section__header > h1 > span:nth-child(2)"
            )[0].get_text().strip()
            if status not in ["Waiting", "Compiling", "Fetched", "Running"]:
                break
            else:
                time.sleep(1)
        if status == "Compile Error": return -1
        resultSet = soup.findAll("td", class_="col--status typo")
        return sum([
            "Accepted" == result.find_all('span')[1].get_text().strip()
            for result in resultSet
        ])

    def getProblemResult(self, homeworkID, problemID, zipPath, lang):
        tryTime = 0
        while True:
            tryTime += 1
            response = self.uploadZip(homeworkID, problemID, zipPath, lang)
            if response.status_code == 200:
                break
            self.logger.error(
                f"{zipPath} {problemID} upload error, code {response.status_code}, url {response.url}"
            )
            time.sleep(1)
        res = self.getProblemStatus(response.url)
        self.logger.debug(
            f"{zipPath} upload succeed, url {response.url}, result {res}")
        return res

    def checkGroupJOJProcess(self, groupNum, hwNum, jojInfo, fns, problemID):
        groupName = f"hgroup-{groupNum:02}"
        hwDir = os.path.join('hwrepos', groupName, f"h{hwNum}")
        if not os.path.exists(hwDir): return 0
        zipPath = os.path.join(hwDir, problemID) + ".zip"
        if os.path.exists(zipPath): os.remove(zipPath)
        with zipfile.ZipFile(zipPath, mode='w') as zf:
            for fn in fns:
                filePath = os.path.join(hwDir, fn)
                if not os.path.exists(filePath):
                    if not fn.endswith(".h"):
                        self.logger.warning(
                            f"{groupName} h{hwNum} {fn} not exist")
                        return 0
                else:
                    zf.write(filePath, fn)
        res = self.getProblemResult(jojInfo["homeworkID"], problemID, zipPath,
                                    jojInfo["lang"])
        # os.remove(zipPath)
        return res

    def checkGroupJOJ(self, jojInfo):
        res = {}
        hwNum = self.args.hw
        for i, (key, value) in enumerate(self.hgroups.items()):
            with multiprocessing.Pool(len(jojInfo["problemInfo"])) as p:
                scores = p.starmap(
                    self.checkGroupJOJProcess,
                    [[i, hwNum, jojInfo, fns, problemID]
                     for fns, problemID, _ in jojInfo["problemInfo"]])
            scores = [(scores[i], jojInfo["problemInfo"][i][2])
                      for i in range(len(scores))]
            self.logger.info(f"{key} h{hwNum} score {scores.__repr__()}")
            jojFailExercise = min(
                sum([
                    int(acCount < 0.25 * totalCount)
                    for acCount, totalCount in scores
                ]), 2)
            jojFailHomework = int(
                sum([item[0] for item in scores]) < 0.5 *
                sum([item[1] for item in scores]))
            jojFailCompile = int(True in [item[0] == -1 for item in scores])
            comments = []
            if jojFailHomework + jojFailExercise + jojFailCompile != 0:
                scoreComments = [
                    f"{fn}: {scores[i][0]}/{scores[i][1]}"
                    for i, (fn, _, _) in enumerate(jojInfo["problemInfo"])
                ]
                comments = [f"JOJ score: {','.join(scoreComments)}"]
            for _, stuName in value:
                res[stuName] = {
                    "jojFailHomework": jojFailHomework,
                    "jojFailExercise": jojFailExercise,
                    "jojFailCompile": jojFailCompile,
                    "jojComment": comments,
                }
        return res

    def checkProjJOJProcess(self, repoName, homeworkID, problemID):
        def zipdir(path, zipPath, zf):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if os.path.join(root, file) == zipPath:
                        continue
                    if 'cmake-build-debug' in root or '.git' in root:
                        continue
                    zf.write(
                        os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file),
                                        os.path.join(path, '.')))

        projDir = os.path.join('projrepos', f'p{self.args.proj}', repoName)
        if not os.path.exists(projDir): return 0
        zipPath = os.path.join(projDir, problemID) + ".zip"
        if os.path.exists(zipPath): os.remove(zipPath)
        with zipfile.ZipFile(zipPath, mode='w') as zf:
            zipdir(projDir, zipPath, zf)
        if self.getProblemResult(homeworkID, problemID, zipPath, "cmake") == 0:
            return 'JOJ copmile success with CMake'
        if self.getProblemResult(homeworkID, problemID, zipPath, "make") == 0:
            return 'JOJ copmile success with GNU Make'
        return 'JOJ copmile failure with both GNU Make and CMake'

    def checkProjJOJ(self, jojInfo):
        res = {}
        projNum, milestoneNum = self.args.proj, self.args.ms
        homeworkID, problemID = jojInfo[projNum]["homeworkID"], jojInfo[projNum]["problemID"]
        infos = [[*info, projNum, milestoneNum]
                 for hgroup in self.hgroups.values() for info in hgroup]
        for id_, name, projNum, milestoneNum in infos:
            repoName = getProjRepoName([id_, name, projNum, milestoneNum])
            comments = [self.checkProjJOJProcess(repoName, homeworkID,
                                                problemID)]
            res[name] = {"jojComment": comments}
        return res


if __name__ == "__main__":
    from settings import *
    res = JOJWorker(JOJ_COURSE_ID,
                    SID).getProblemResult("5f66161a91df0600062ff7aa",
                                          "5f6614eb91df0600062ff7a7",
                                          "ex2.zip", "matlab")
    print(res)