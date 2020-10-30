from canvasapi import Canvas
from util import first, Logger
import json


class CanvasWorker():
    def __init__(self,
                 args,
                 rubric,
                 canvasToken,
                 courseID,
                 names,
                 indvScores,
                 groupScores,
                 jojScores,
                 totalScores=None,
                 logger=Logger()):
        self.args = args
        self.rubric = rubric
        self.canvas = Canvas("https://umjicanvas.com/", canvasToken)
        self.course = self.canvas.get_course(courseID)
        self.users = self.course.get_users()
        self.assignments = self.course.get_assignments()
        self.logger = logger
        self.scores = {}
        if totalScores is None:
            self.names = names
            for key in names:
                self.scores[key] = {
                    **indvScores.get(key, {}),
                    **groupScores.get(key, {}),
                    **jojScores.get(key, {})
                }
        else:
            self.scores = totalScores

    def generateHomeworkData(self, scoreInfo):
        score = 0
        comment = []
        for key, value in self.rubric.items():
            for _ in range(scoreInfo.get(key, 0)):
                score += value[0]
                comment.append(f"{value[1]}, {value[0]}")
        if not comment:
            comment = ['good job']
        else:
            comment.insert(0, "Genral Info:")
            comment.append("")
            comment.append("Detail:")
            comment.extend(
                scoreInfo.get("indvComment", []) +
                scoreInfo.get("groupComment", []) +
                scoreInfo.get("jojComment", []))
        return {
            'submission': {
                'posted_grade': max(score, -2.5)
            },
            'comment': {
                'text_comment': '\n'.join(comment)
            },
        }

    def grade2Canvas(self):
        hwNum = self.args.hw
        assignment = first(self.assignments,
                           lambda x: x.name.startswith(f"h{hwNum}"))
        for submission in assignment.get_submissions():
            currentUser = first(self.users,
                                lambda user: user.id == submission.user_id)
            if currentUser is None: continue
            name = currentUser.name.strip()
            if name not in self.names: continue
            if not self.scores[name]: continue
            data = self.generateHomeworkData(self.scores[name])
            self.logger.debug(f"{name} {data.__repr__()}")
            submission.edit(**data)

    def exportScores(self, fileName):
        json.dump(self.scores,
                  open(fileName, "w"),
                  ensure_ascii=False,
                  indent=4)
        self.logger.debug(f"score dump to {fileName} succeed")