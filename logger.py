# -*- coding: utf-8 -*-
# @Name    : logger
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-20 上午10:46


import os

from logging import (
    Formatter,
    getLogger,
    Handler,
    INFO,
    Logger,
    LogRecord,
    StreamHandler,
)

from logging.handlers import (
    RotatingFileHandler,
    QueueListener,
    QueueHandler as BaseQueueHandler
)
from queue import SimpleQueue as Queue

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_handler = RotatingFileHandler(filename=BASE_DIR + "/logs/manager.log",
                                   maxBytes=300 * 1024 * 1024,
                                   backupCount=10)
crash_file_handler = RotatingFileHandler(filename=BASE_DIR + "/logs/crash.log",
                                         maxBytes=300 * 1024 * 1024,
                                         backupCount=10)
file_handler.setFormatter(Formatter('%(levelname)s--%(asctime)s--%(module)s--%(pathname)s: %(lineno)d %(message)s'))
crash_file_handler.setFormatter(
    Formatter('%(levelname)s--%(asctime)s--%(module)s--%(pathname)s: %(lineno)d %(message)s'))

console_handler = StreamHandler()
console_handler.setFormatter(Formatter('%(levelname)s--%(asctime)s--%(module)s--%(pathname)s: %(lineno)d %(message)s'))


class QueueHandler(BaseQueueHandler):

    def prepare(self, record: LogRecord) -> LogRecord:
        return record


def setup_logging_queue(*handlers: Handler) -> QueueHandler:
    queue: Queue = Queue()
    queue_handler = QueueHandler(queue)
    listener = QueueListener(queue, *handlers, respect_handler_level=True)
    listener.start()
    return queue_handler


def new_logger(level=INFO) -> Logger:
    logger = getLogger("Logger")
    logger.setLevel(level)
    queue_handler = setup_logging_queue(file_handler, console_handler)
    logger.addHandler(queue_handler)
    return logger


def new_crash_logger(level=INFO) -> Logger:
    logger = getLogger("CrashLogger")
    logger.setLevel(level)
    queue_handler = setup_logging_queue(crash_file_handler, console_handler)
    logger.addHandler(queue_handler)
    return logger


logger = new_logger(INFO)
crash_logger = new_crash_logger(INFO)
