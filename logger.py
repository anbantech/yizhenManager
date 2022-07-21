# -*- coding: utf-8 -*-
# @Name    : logger
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-20 上午10:46


import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config = {

    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s--%(asctime)s--%(module)s--%(pathname)s: %(lineno)d %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },

        'manager_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': (BASE_DIR + "/logs/manager.log"),
            'maxBytes': 300 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose'
        },

    },
    'loggers': {
        'Logger': {
            'handlers': ['manager_file', "console"],
            'propagate': True,
            'level': 'INFO',
        }
    }
}
