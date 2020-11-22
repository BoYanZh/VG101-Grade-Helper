from util import Logger, getProjRepoName, passCodeQuality, getAllFiles
from shutil import ignore_patterns, copytree, rmtree
import multiprocessing
import traceback
import git
import os


class GitWorker():
    def __init__(self,
                 args,
                 hgroups,
                 pgroups,
                 language,
                 mandatoryFiles,
                 optionalFiles,
                 logger=Logger(),
                 processCount=4):
        self.args = args
        self.hgroups = hgroups
        self.pgroups = pgroups
        self.language = language
        self.logger = logger
        self.processCount = processCount
        self.mandatoryFiles = mandatoryFiles
        self.optionalFiles = optionalFiles
        self.moss = None

    @classmethod
    def isREADME(cls, fn):
        fn = fn.lower()
        if len(fn) < 6: return False
        if len(fn) == 6: return fn == "readme"
        return fn[:7] == "readme."

    def checkIndvProcess(self, groupNum, hwNum):
        tidy = self.args.tidy
        repoName = f"hgroup-{groupNum:02}"
        repoDir = os.path.join("hwrepos", repoName)
        hwDir = os.path.join(repoDir, f"h{hwNum}")
        if not os.path.exists(repoDir):
            repo = git.Repo.clone_from(
                f"https://focs.ji.sjtu.edu.cn/git/vg101/{repoName}",
                repoDir,
                branch="master")
        else:
            repo = git.Repo(repoDir)
        repo.git.fetch("--all", "-f")
        remoteBranches = [ref.name for ref in repo.remote().refs]
        scores = {
            stuName: {
                "indvFailSubmit": 0,
                "indvUntidy": 0,
                "indvLowCodeQuality": 0,
                "indvComment": [],
            }
            for _, stuName in self.hgroups[repoName]
        }
        for stuID, stuName in self.hgroups[repoName]:
            try:
                if f"origin/{stuID}" not in remoteBranches:
                    self.logger.warning(
                        f"{repoName} {stuID} {stuName} branch missing")
                    scores[stuName]["indvFailSubmit"] = 1
                    scores[stuName]["indvComment"].append(
                        "individual branch individual branch missing")
                    continue
                repo.git.reset("--hard", f"origin/{stuID}")
                repo.git.clean("-d", "-f", "-x")
                self.logger.debug(f"{repoName} {stuID} {stuName} pull succeed")
                if self.args.dir:
                    copytree(repoDir,
                             os.path.join("indv",
                                          f"{repoName} {stuID} {stuName}"),
                             ignore=ignore_patterns(".git"))
                if not os.path.exists(hwDir):
                    self.logger.warning(
                        f"{repoName} {stuID} {stuName} h{hwNum} dir missing")
                    scores[stuName]["indvFailSubmit"] = 1
                    scores[stuName]["indvComment"].append(
                        f"individual branch h{hwNum} dir missing")
                else:
                    for fn, path in [
                        (fn, os.path.join(hwDir, fn)) for fn in
                        [*self.mandatoryFiles, *self.optionalFiles]
                    ]:
                        if os.path.exists(path):
                            if not passCodeQuality(path, self.language):
                                scores[stuName]["indvLowCodeQuality"] = 1
                                scores[stuName]["indvComment"].append(
                                    f"individual {fn} low quality")
                                self.logger.warning(
                                    f"{repoName} {stuID} {stuName} {fn} low quality"
                                )
                            continue
                        if fn in self.mandatoryFiles:
                            self.logger.warning(
                                f"{repoName} {stuID} {stuName} h{hwNum}/{fn} file missing"
                            )
                            scores[stuName]["indvFailSubmit"] = 1
                            scores[stuName]["indvComment"].append(
                                f"individual branch h{hwNum}/{fn} file missing"
                            )
                    if not list(filter(GitWorker.isREADME, os.listdir(hwDir))):
                        self.logger.warning(
                            f"{repoName} {stuID} {stuName} h{hwNum}/README file missing"
                        )
                        scores[stuName]["indvFailSubmit"] = 1
                        scores[stuName]["indvComment"].append(
                            f"individual branch h{hwNum}/README file missing")
                if not tidy: continue
                dirList = list(
                    filter(
                        lambda x: x not in
                        [".gitignore", ".git", *[f"h{n}" for n in range(20)]
                         ] and not GitWorker.isREADME(x), os.listdir(repoDir)))
                if dirList:
                    self.logger.warning(
                        f"{repoName} {stuID} {stuName} untidy {', '.join(dirList)}"
                    )
                    scores[stuName]["indvUntidy"] = 1
                    scores[stuName]["indvComment"].append(
                        f"individual branch redundant files: {', '.join(dirList)}"
                    )
                if os.path.exists(hwDir):
                    dirList = os.listdir(hwDir)
                    dirList = list(
                        filter(
                            lambda x: x not in self.mandatoryFiles and x not in
                            self.optionalFiles and not GitWorker.isREADME(x),
                            dirList))
                    if dirList:
                        self.logger.warning(
                            f"{repoName} {stuID} {stuName} h{hwNum}/ untidy {', '.join(dirList)}"
                        )
                        scores[stuName]["indvUntidy"] = 1
                        scores[stuName]["indvComment"].append(
                            f"individual branch redundant files: {', '.join(dirList)}"
                        )
            except Exception:
                self.logger.error(f"{repoName} {stuID} {stuName} error")
                self.logger.error(traceback.format_exc())
        return scores

    def checkGroupProcess(self, groupNum, hwNum):
        tidy = self.args.tidy
        repoName = f"hgroup-{groupNum:02}"
        repoDir = os.path.join("hwrepos", repoName)
        hwDir = os.path.join(repoDir, f"h{hwNum}")
        if not os.path.exists(repoDir):
            repo = git.Repo.clone_from(
                f"https://focs.ji.sjtu.edu.cn/git/vg101/{repoName}",
                repoDir,
                branch="master")
        else:
            repo = git.Repo(repoDir)
        repo.git.fetch("--tags", "--all", "-f")
        tagNames = [tag.name for tag in repo.tags]
        scores = {
            stuName: {
                "groupFailSubmit": 0,
                "groupUntidy": 0,
                "groupLowCodeQuality": 0,
                "groupComment": [],
            }
            for _, stuName in self.hgroups[repoName]
        }
        if f"h{hwNum}" not in tagNames:
            self.logger.warning(f"{repoName} tags/h{hwNum} missing")
            for _, stuName in self.hgroups[repoName]:
                scores[stuName]["groupFailSubmit"] = 1
                scores[stuName]["groupComment"].append(
                    f"tags/h{hwNum} missing")
            return scores
        repo.git.reset("--hard", f"origin/master")
        repo.git.clean("-d", "-f", "-x")
        repo.git.checkout(f"tags/h{hwNum}")
        self.logger.debug(f"{repoName} checkout to tags/h{hwNum} succeed")
        if not os.path.exists(hwDir):
            self.logger.warning(f"{repoName} h{hwNum} dir missing")
            for _, stuName in self.hgroups[repoName]:
                scores[stuName]["groupFailSubmit"] = 1
                scores[stuName]["groupComment"].append(
                    f"tags/h{hwNum} h{hwNum} dir missing")
        else:
            for fn, path in [
                (fn, os.path.join(hwDir, fn))
                    for fn in [*self.mandatoryFiles, *self.optionalFiles]
            ]:
                if os.path.exists(path):
                    if not passCodeQuality(path, self.language):
                        for _, stuName in self.hgroups[repoName]:
                            scores[stuName]["groupLowCodeQuality"] = 1
                            scores[stuName]["groupComment"].append(
                                f"group {fn} low quality")
                        self.logger.warning(f"{repoName} {fn} low quality")
                    continue
                if fn in self.mandatoryFiles:
                    self.logger.warning(
                        f"{repoName} h{hwNum}/{fn} file missing")
                    for _, stuName in self.hgroups[repoName]:
                        scores[stuName]["groupFailSubmit"] = 1
                        scores[stuName]["groupComment"].append(
                            f"tags/h{hwNum} h{hwNum}/{fn} missing")
            if not list(filter(GitWorker.isREADME, os.listdir(hwDir))):
                self.logger.warning(f"{repoName} h{hwNum}/README file missing")
                for _, stuName in self.hgroups[repoName]:
                    scores[stuName]["groupFailSubmit"] = 1
                    scores[stuName]["groupComment"].append(
                        f"tags/h{hwNum} h{hwNum}/README file missing")
        if not tidy: return scores
        dirList = os.listdir(repoDir)
        if os.path.exists(os.path.join(repoDir, ".gitea")):
            dirList.extend([
                fn for fn in os.listdir(os.path.join(repoDir, ".gitea"))
                if fn != "pull_request_template.md"
            ])
        dirList = list(
            filter(
                lambda x: x not in [
                    ".gitignore", ".git", ".gitea",
                    *[f"h{n}" for n in range(20)]
                ] and not GitWorker.isREADME(x), dirList))
        if dirList:
            self.logger.warning(f"{repoName} untidy {', '.join(dirList)}")
            for _, stuName in self.hgroups[repoName]:
                scores[stuName]["groupUntidy"] = 1
                scores[stuName]["groupComment"].append(
                    f"tags/h{hwNum} redundant files: {', '.join(dirList)}")
        if os.path.exists(hwDir):
            dirList = os.listdir(hwDir)
            dirList = list(
                filter(
                    lambda x: x not in self.mandatoryFiles and x not in self.
                    optionalFiles and not GitWorker.isREADME(x), dirList))
            if dirList:
                self.logger.warning(
                    f"{repoName} h{hwNum} untidy {', '.join(dirList)}")
                for _, stuName in self.hgroups[repoName]:
                    scores[stuName]["groupUntidy"] = 1
                    scores[stuName]["groupComment"].append(
                        f"tags/h{hwNum} redundant files: {', '.join(dirList)}")
        return scores

    def checkProjProcess(self, id_, name, projNum, milestoneNum):
        stuName = name
        repoName = getProjRepoName([id_, name, projNum, milestoneNum])
        repoDir = os.path.join("projrepos", f"p{projNum}", repoName)
        scores = {
            stuName: {
                "projComment": [],
            }
        }
        if not os.path.exists(repoDir):
            repo = git.Repo.clone_from(
                f"https://focs.ji.sjtu.edu.cn/git/vg101/{repoName}", repoDir)
        else:
            repo = git.Repo(os.path.join("projrepos", f"p{projNum}", repoName))
            repo.git.fetch("--tags", "--all", "-f")
            remoteBranches = [ref.name for ref in repo.remote().refs]
            if "origin/master" not in remoteBranches:
                self.logger.warning(f"{repoName} master branch missing")
                scores[stuName]["projComment"].append(f"master branch missing")
                return scores
            repo.git.reset("--hard", "origin/master")
            repo.git.clean("-d", "-f", "-x")
        if milestoneNum:
            repo.git.fetch("--tags", "--all", "-f")
            tagNames = [tag.name for tag in repo.tags]
            if f"m{milestoneNum}" not in tagNames:
                self.logger.warning(f"{repoName} tags/m{milestoneNum} missing")
                scores[stuName]["projComment"].append(
                    f"tags/m{milestoneNum} missing")
                return scores
            repo.git.checkout(f"tags/m{milestoneNum}", "-f")
            self.logger.debug(
                f"{repoName} checkout to tags/m{milestoneNum} succeed")
            if not list(filter(GitWorker.isREADME, os.listdir(repoDir))):
                self.logger.warning(f"{repoName} README file missing")
                scores[stuName]["projComment"].append(f"README file missing")
            language = ["matlab", "c"]
            if projNum == 1:
                for fn in getAllFiles(repoDir):
                    if (fn.endswith(".m")) and not passCodeQuality(
                            os.path.join(repoDir, fn), language[projNum - 1]):
                        self.logger.warning(f"{repoName} {fn} low quality")
                        scores[stuName]["projComment"].append(
                            f"{fn} low quality")
            elif projNum == 2:
                for fn in getAllFiles(repoDir):
                    if (fn.endswith(".c")
                            or fn.endswith(".h")) and not passCodeQuality(
                                os.path.join(repoDir, fn),
                                language[projNum - 1]):
                        self.logger.warning(f"{repoName} {fn} low quality")
                        scores[stuName]["projComment"].append(
                            f"{fn} low quality")
        else:
            self.logger.debug(f"{repoName} pull succeed")
        return scores

    def checkProj3Process(self, groupNum, milestoneNum):
        repoName = f"p3group-{groupNum:02}"
        repoDir = os.path.join("projrepos", "p3", repoName)
        students = self.pgroups[repoName]
        scores = {stuInfo[1]: {"projComment": []} for stuInfo in students}
        if not os.path.exists(repoDir):
            repo = git.Repo.clone_from(
                f"https://focs.ji.sjtu.edu.cn/git/vg101/{repoName}", repoDir)
        else:
            repo = git.Repo(os.path.join("projrepos", f"p3", repoName))
            repo.git.fetch("--tags", "--all", "-f")
            remoteBranches = [ref.name for ref in repo.remote().refs]
            if "origin/master" not in remoteBranches:
                self.logger.warning(f"{repoName} master branch missing")
                for stuInfo in students:
                    scores[stuInfo[1]]["projComment"].append(
                        f"master branch missing")
                return scores
            repo.git.reset("--hard", "origin/master")
            repo.git.clean("-d", "-f", "-x")
        if milestoneNum:
            repo.git.fetch("--tags", "--all", "-f")
            tagNames = [tag.name for tag in repo.tags]
            if f"m{milestoneNum}" not in tagNames:
                self.logger.warning(f"{repoName} tags/m{milestoneNum} missing")
                for stuInfo in students:
                    scores[stuInfo[1]]["projComment"].append(
                        f"tags/m{milestoneNum} missing")
                return scores
            repo.git.checkout(f"tags/m{milestoneNum}", "-f")
            self.logger.debug(
                f"{repoName} checkout to tags/m{milestoneNum} succeed")
            if not list(filter(GitWorker.isREADME, os.listdir(repoDir))):
                self.logger.warning(f"{repoName} README file missing")
                for stuInfo in students:
                    scores[stuInfo[1]]["projComment"].append(
                        f"README file missing")
            for fn in getAllFiles(repoDir):
                if (any(
                    (fn.endswith(suf)
                     for suf in [".c", ".cc", ".cpp", ".hpp", ".h", ".cxx"]))
                    ) and not passCodeQuality(os.path.join(repoDir, fn), "cc"):
                    self.logger.warning(f"{repoName} {fn} low quality")
                    for stuInfo in students:
                        scores[stuInfo[1]]["projComment"].append(
                            f"{fn} low quality")
        else:
            self.logger.debug(f"{repoName} pull succeed")
        return scores

    def checkIndv(self):
        if self.args.dir:
            if os.path.exists(os.path.join("indv")):
                rmtree(os.path.join("indv"))
        hwNum = self.args.hw
        if self.args.rejudge < 0:
            with multiprocessing.Pool(self.processCount) as p:
                res = p.starmap(self.checkIndvProcess,
                                [(i, hwNum)
                                 for i in range(len(self.hgroups.keys()))])
        else:
            res = [self.checkIndvProcess(self.args.rejudge, hwNum)]
        return {k: v for d in res for k, v in d.items()}

    def checkGroup(self):
        hwNum = self.args.hw
        if self.args.rejudge < 0:
            with multiprocessing.Pool(self.processCount) as p:
                res = p.starmap(self.checkGroupProcess,
                                [(i, hwNum)
                                 for i in range(len(self.hgroups.keys()))])
        else:
            res = [self.checkGroupProcess(self.args.rejudge, hwNum)]
        return {k: v for d in res for k, v in d.items()}

    def checkProj(self, projNum, milestoneNum):
        milestoneNum = 0 if milestoneNum is None else milestoneNum
        res = {}
        if projNum in [1, 2]:
            infos = [[*info, projNum, milestoneNum]
                     for hgroup in self.hgroups.values() for info in hgroup]
            with multiprocessing.Pool(self.processCount) as p:
                res = p.starmap(self.checkProjProcess, infos)
        elif projNum in [3]:
            infos = [[i, milestoneNum] for i in range(len(self.pgroups.keys()))]
            with multiprocessing.Pool(self.processCount) as p:
                res = p.starmap(self.checkProj3Process, infos)
        return {k: v for d in res for k, v in d.items()}