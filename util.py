import logging


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