from util import Logger, getProjRepoName
import requests


class GiteaWorker():
    def __init__(self, args, baseUrl, orgName, token, hgroups,
                 logger=Logger()):
        self.args = args
        self.logger = logger
        self.names = {
            item[1]: item[0]
            for items in hgroups.values() for item in items
        }
        self.ids = {
            item[0]: item[1]
            for items in hgroups.values() for item in items
        }
        self.hgroups = hgroups
        self.baseUrl = baseUrl
        self.orgName = orgName
        self.sess = requests.Session()
        self.sess.params.update({"access_token": token})

    def raiseIssues(self, scores):
        for key, value in scores.items():
            if not value.get('projComment'):
                value['projComment'] = ['good job']
            if not value.get('jojComment'):
                value['jojComment'] = ['']
            id_ = self.names[key]
            repoName = getProjRepoName([id_, key, self.args.proj])
            url = f"{self.baseUrl}/repos/{self.orgName}/{repoName}/issues"
            data = {
                "title": f"m{self.args.ms} feedback",
                "body": '\n'.join([*value['projComment'], *value['jojComment']]),
            }
            req = self.sess.post(url, data)
            self.logger.debug(f"{repoName} issue {req.status_code} {req.text}")

    def checkReview(self):
        hwNum = self.args.hw
        res = {key: {"noReview": 1} for key in self.names.keys()}
        for repoName, users in self.hgroups.items():
            url = f"{self.baseUrl}/repos/{self.orgName}/{repoName}/pulls"
            pulls = self.sess.get(url).json()
            for pull in pulls:
                if not pull["title"].startswith(f"h{hwNum}"): continue
                url = f"{self.baseUrl}/repos/{self.orgName}/{repoName}/pulls/{pull['number']}/reviews"
                self.logger.info(f"{repoName} h{hwNum} get pr: {url}")
                for item in self.sess.get(url).json():
                    stuID = ''.join(
                        [s for s in item['user']['full_name'] if s.isdigit()])
                    if self.ids.get(stuID):
                        name = self.ids[stuID]
                        res[name]["noReview"] = 0
                        self.logger.info(f"{repoName} h{hwNum} {stuID} {name} reviewed")
        return res