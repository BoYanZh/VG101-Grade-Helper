from canvasapi import Canvas
from util import first, Logger
import json


class CanvasWorker():
    def __init__(self,
                 args,
                 rubric,
                 canvasToken,
                 courseID,
                 indvScores,
                 groupScores,
                 jojScores,
                 logger=Logger()):
        self.args = args
        self.rubric = rubric
        self.canvas = Canvas("https://umjicanvas.com/", canvasToken)
        self.course = self.canvas.get_course(courseID)
        self.users = self.course.get_users()
        self.assignments = self.course.get_assignments()
        self.logger = logger
        if not indvScores or not groupScores or not jojScores:
            raise Exception("Not enough scores")
        self.scores = indvScores
        for key, value in self.scores.items():
            self.scores[key] = {
                **value,
                **groupScores[key],
                **jojScores[key]
            }

    def generateHomeworkData(self, scoreInfo):
        score = 0
        comment = []
        for key, value in self.rubric:
            for _ in range(scoreInfo[key]):
                score -= value[0]
                comment.append(value[1])
        if not comment: comment = ['good job']
        return {
            'submission': {
                'posted_grade': score
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
            data = self.generateHomeworkData(self.scores[name])
            submission.edit(**data)

    def exportScores(self, fileName):
        json.dump(self.scores,
                  open(fileName, "w"),
                  ensure_ascii=False,
                  indent=4)
        self.logger.debug("score dump to score.json succeed")