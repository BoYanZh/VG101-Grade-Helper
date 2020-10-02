from shutil import ignore_patterns, copytree, rmtree
from util import Logger
import multiprocessing
import git
import os
import re


class GiteaWorker():
    def __init__(self,
                 args,
                 hgroups,
                 mandatoryFiles,
                 logger=Logger(),
                 processCount=16):
        self.args = args
        self.hgroups = hgroups
        self.logger = logger
        self.processCount = processCount
        self.mandatoryFiles = mandatoryFiles

    def checkProjRepoName(self, arg):
        id_, name, projNum, *_ = arg
        eng = re.sub('[\u4e00-\u9fa5]', '', name)
        eng = ''.join(
            [word[0].capitalize() + word[1:] for word in eng.split()])
        return f"{eng}{id_}-p{projNum}"

    def checkIndvProcess(self, groupNum, hwNum, tidy):
        repoName = f"hgroup-{groupNum:02}"
        if not os.path.exists(os.path.join('hwrepos', repoName)):
            repo = git.Repo.clone_from(
                f"https://focs.ji.sjtu.edu.cn/git/vg101/{repoName}",
                os.path.join('hwrepos', repoName),
                branch='master')
        else:
            repo = git.Repo(os.path.join('hwrepos', repoName))
        repo.git.fetch()
        remoteBranches = [ref.name for ref in repo.remote().refs]
        scores = {
            stuName: {
                "indvFailSubmit": 0,
                "indvUntidy": 0,
            }
            for _, stuName in self.hgroups[repoName]
        }
        for stuID, stuName in self.hgroups[repoName]:
            try:
                if f"origin/{stuID}" not in remoteBranches:
                    self.logger.warning(
                        f"{repoName} {stuID} {stuName} branch missing")
                    scores[stuName]['indvFailSubmit'] = 1
                    continue
                repo.git.checkout(f"{stuID}", "-f")
                repo.git.pull("origin", f"{stuID}", "--rebase", "-f")
                repo.git.reset(f"origin/{stuID}", "--hard")
                if self.args.dir:
                    copytree(os.path.join('hwrepos', repoName),
                            os.path.join('indv', f"{repoName} {stuID} {stuName}"),
                            ignore=ignore_patterns('.git'))
                if not os.path.exists(
                        os.path.join('hwrepos', repoName, f"h{hwNum}")):
                    self.logger.warning(
                        f"{repoName} {stuID} {stuName} h{hwNum} dir missing")
                    scores[stuName]['indvFailSubmit'] = 1
                for path in [
                        os.path.join('hwrepos', repoName, f"h{hwNum}", fn)
                        for fn in self.mandatoryFiles
                ]:
                    if not os.path.exists(path):
                        self.logger.warning(
                            f"{repoName} {stuID} {stuName} h{hwNum} file missing"
                        )
                        scores[stuName]['indvFailSubmit'] = 1
                self.logger.debug(f"{repoName} {stuID} {stuName} succeed")
                if tidy:
                    dirList = os.listdir(os.path.join('hwrepos', repoName))
                    dirList = list(
                        filter(
                            lambda x: x not in [
                                "README.md", ".git",
                                *[f"h{n}" for n in range(20)]
                            ], dirList))
                    if dirList:
                        self.logger.warning(
                            f"{repoName} {stuID} {stuName} untidy")
                        scores[stuName]['indvUntidy'] = 1
            except:
                self.logger.error(f"{repoName} {stuID} {stuName} error")
        return scores

    def checkGroupProcess(self, groupNum, hwNum, tidy):
        repoName = f"hgroup-{groupNum:02}"
        if not os.path.exists(os.path.join('hwrepos', repoName)):
            repo = git.Repo.clone_from(
                f"https://focs.ji.sjtu.edu.cn/git/vg101/{repoName}",
                os.path.join('hwrepos', repoName),
                branch='master')
        else:
            repo = git.Repo(os.path.join('hwrepos', repoName))
        repo.git.checkout("master", "-f")
        repo.git.fetch("--tags", "-f")
        tagNames = [tag.name for tag in repo.tags]
        scores = {
            stuName: {
                "groupFailSubmit": 0,
                "groupUntidy": 0,
            }
            for _, stuName in self.hgroups[repoName]
        }
        if f"h{hwNum}" not in tagNames:
            self.logger.warning(f"{repoName} tags/h{hwNum} missing")
            for _, stuName in self.hgroups[repoName]:
                scores[stuName]['groupFailSubmit'] = 1
            return
        repo.git.checkout(f"tags/h{hwNum}", "-f")
        if not os.path.exists(os.path.join('hwrepos', repoName, f"h{hwNum}")):
            self.logger.warning(f"{repoName} h{hwNum} dir missing")
            for _, stuName in self.hgroups[repoName]:
                scores[stuName]['groupFailSubmit'] = 1
        for path in [
                os.path.join('hwrepos', repoName, f"h{hwNum}", fn)
                for fn in self.mandatoryFiles
        ]:
            if not os.path.exists(path):
                self.logger.warning(f"{repoName} h{hwNum} file missing")
                for _, stuName in self.hgroups[repoName]:
                    scores[stuName]['groupFailSubmit'] = 1
        self.logger.debug(f"{repoName} checkout to tags/h{hwNum} succeed")
        if tidy:
            dirList = os.listdir(os.path.join('hwrepos', repoName))
            dirList = list(
                filter(
                    lambda x: x not in
                    ["README.md", ".git", *[f"h{n}" for n in range(20)]],
                    dirList))
            if dirList:
                self.logger.warning(f"{repoName} untidy")
                for _, stuName in self.hgroups[repoName]:
                    scores[stuName]['groupUntidy'] = 1
        return scores

    def checkProjProcess(self, id_, name, projNum, milestoneNum):
        repoName = self.checkProjRepoName([id_, name, projNum, milestoneNum])
        repoDir = os.path.join('projrepos', f'p{projNum}', repoName)
        if not os.path.exists(repoDir):
            repo = git.Repo.clone_from(
                f"https://focs.ji.sjtu.edu.cn/git/vg101/{repoName}", repoDir)
        else:
            repo = git.Repo(os.path.join('projrepos', f'p{projNum}', repoName))
            repo.git.fetch()
            remoteBranches = [ref.name for ref in repo.remote().refs]
            if 'origin/master' not in remoteBranches:
                self.logger.warning(f"{repoName} branch master missing")
                return
            repo.git.checkout(f"master", "-f")
            repo.git.pull("origin", "master", "--rebase", "-f")
            repo.git.reset('--hard')
        if not list(
                filter(lambda x: x.lower().startswith('readme'),
                       os.listdir(repoDir))):
            self.logger.warning(f"{repoName} README missing")
        if milestoneNum:
            tagNames = [tag.name for tag in repo.tags]
            if f"m{milestoneNum}" not in tagNames:
                self.logger.warning(f"{repoName} tags/m{milestoneNum} missing")
                return
            repo.git.checkout(f"tags/m{milestoneNum}", "-f")
            self.logger.debug(
                f"{repoName} checkout to tags/m{milestoneNum} succeed")
        else:
            self.logger.debug(f"{repoName} pull succeed")

    def checkIndv(self):
        if self.args.dir:
            if os.path.exists(os.path.join('indv')):
                rmtree(os.path.join('indv'))
        hwNum, tidy = self.args.hw, self.args.tidy
        with multiprocessing.Pool(self.processCount) as p:
            res = p.starmap(self.checkIndvProcess,
                            [(i, hwNum, tidy) for i in range(26)])
        return {k: v for d in res for k, v in d.items()}

    def checkGroup(self):
        hwNum, tidy = self.args.hw, self.args.tidy
        with multiprocessing.Pool(self.processCount) as p:
            res = p.starmap(self.checkGroupProcess,
                            [(i, hwNum, tidy) for i in range(26)])
        return {k: v for d in res for k, v in d.items()}

    def checkProj(self, projNum, milestoneNum):
        milestoneNum = 0 if milestoneNum is None else milestoneNum
        if projNum in [1, 2]:
            infos = [[*info, projNum, milestoneNum]
                     for hgroup in self.hgroups.values() for info in hgroup]
        elif projNum in [3]:
            infos = []
            return
        else:
            return
        with multiprocessing.Pool(self.processCount) as p:
            p.starmap(self.checkProjProcess, infos)