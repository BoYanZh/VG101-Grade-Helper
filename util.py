import subprocess
import logging
import os
import re


class Logger():
    _instance = None

    def __new__(cls, fileName="VG101GradeHelper.log", loggerName="myLogger"):
        if cls._instance is None:
            logger = logging.getLogger(loggerName)
            formatter = logging.Formatter(
                '[%(asctime)s][%(levelname)8s][%(filename)s %(lineno)3s]%(message)s'
            )
            logger.setLevel(logging.DEBUG)
            streamHandler = logging.StreamHandler()
            streamHandler.setFormatter(formatter)
            streamHandler.setLevel(logging.WARNING)
            fileHandler = logging.FileHandler(filename=fileName)
            fileHandler.setFormatter(formatter)
            fileHandler.setLevel(logging.DEBUG)
            logger.addHandler(fileHandler)
            logger.addHandler(streamHandler)
            cls._instance = logger
        return cls._instance


def first(iterable, condition=lambda x: True):
    try:
        return next(x for x in iterable if condition(x))
    except StopIteration:
        return None


def getProjRepoName(arg):
    id_, name, projNum, *_ = arg
    eng = re.sub('[\u4e00-\u9fa5]', '', name)
    eng = ''.join([word[0].capitalize() + word[1:] for word in eng.split()])
    return f"{eng}{id_}-p{projNum}"


def passCodeQuality(path, language):
    if language == "matlab":
        with open(path, encoding='utf-8', errors='replace') as f:
            res = f.read()
        return "global " not in res
    if language == "c":
        res = subprocess.check_output(
            ["ctags", "-R", "-x", "--sort=yes", "--c-kinds=v", path])
        lines = res.splitlines()
        return len([line for line in lines if b"const" not in line]) == 0


def getAllFiles(root):
    for f in os.listdir(root):
        if os.path.isfile(os.path.join(root, f)):
            yield os.path.join(f)
    dirs = [
        d for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d)) and d != ".git"
    ]
    for d in dirs:
        dirfiles = getAllFiles(os.path.join(root, d))
        for f in dirfiles:
            yield os.path.join(d, f)
