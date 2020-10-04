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
        self.baseUrl = baseUrl
        self.orgName = orgName
        self.sess = requests.Session()
        self.sess.params.update({"access_token": token})

    def raiseIssues(self, scores):
        for key, value in scores.items():
            if not value.get('projComment'):
                value['projComment'] = ['good job']
            id_ = self.names[key]
            repoName = getProjRepoName([id_, key, self.args.proj])
            url = f"{self.baseUrl}/repos/{self.orgName}/{repoName}/issues"
            data = {
                "title": f"m{self.args.ms} feedback",
                "body": '\n'.join(value['projComment']),
            }
            req = self.sess.post(url, data)
            self.logger.debug(f"{repoName} issue {req.status_code} {req.text}")
