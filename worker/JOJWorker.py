from bs4 import BeautifulSoup
from util import Logger
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
            if status not in ["Waiting", "Compiling", "Pending", "Running"]:
                break
            else:
                time.sleep(1)
        resultSet = soup.findAll("td", class_="col--status typo")
        acCount = 0
        for result in resultSet:
            if "Accepted" == result.find_all('span')[1].get_text().strip():
                acCount += 1
        return acCount

    def getProblemResult(self,
                         homeworkID,
                         problemID,
                         zipPath,
                         lang,
                         groupName='',
                         fn='',
                         hwNum=0):
        tryTime = 0
        while True:
            tryTime += 1
            response = self.uploadZip(homeworkID, problemID, zipPath, lang)
            if response.status_code != 200:
                self.logger.error(
                    f"{groupName} h{hwNum} {fn} upload error, code {response.status_code}"
                )
            else:
                break
        self.logger.debug(
            f"{groupName} h{hwNum} {fn} upload succeed {response.url}")
        return self.getProblemStatus(response.url)

    def checkGroupJOJProcess(self, groupNum, hwNum, jojInfo, fn, problemID):
        groupName = f"hgroup-{groupNum:02}"
        hwDir = os.path.join('hwrepos', groupName, f"h{hwNum}")
        filePath = os.path.join(hwDir, fn)
        if not os.path.exists(filePath): return 0
        with zipfile.ZipFile(filePath + ".zip", mode='w') as zf:
            zf.write(filePath, fn)
        res = self.getProblemResult(jojInfo["homeworkID"], problemID,
                                    filePath + ".zip", jojInfo["lang"],
                                    groupName, fn, hwNum)
        return res

    def checkGroupJOJ(self, jojInfo):
        res = {}
        hwNum = self.args.hw
        for i, (key, value) in enumerate(self.hgroups.items()):
            with multiprocessing.Pool(len(jojInfo["problemInfo"])) as p:
                scores = p.starmap(
                    self.checkGroupJOJProcess,
                    [[i, hwNum, jojInfo, fn, problemID]
                     for fn, problemID, _ in jojInfo["problemInfo"]])
            scores = [(scores[i], jojInfo["problemInfo"][i][2])
                      for i in range(len(scores))]
            jojFailExercise = min(
                sum([
                    int(acCount < 0.25 * totalCount)
                    for acCount, totalCount in scores
                ]), 2)
            self.logger.info(f"{key} h{hwNum} score {scores.__repr__()}")
            jojFailHomework = int(
                sum([item[0] for item in scores]) < 0.5 *
                sum([item[1] for item in scores]))
            for _, stuName in value:
                res[stuName] = {
                    "jojFailHomework": jojFailHomework,
                    "jojFailExercise": jojFailExercise
                }
        return res


if __name__ == "__main__":
    from settings import *
    res = JOJWorker(JOJ_COURSE_ID,
                    SID).getProblemResult("5f66161a91df0600062ff7aa",
                                          "5f6614eb91df0600062ff7a7",
                                          "ex2.zip", "matlab")
    print(res)