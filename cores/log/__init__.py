#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
from logging.handlers import RotatingFileHandler
import logging
import logging.config


def configure_logger(name, log_path, console_level="INFO", file_level="INFO"):
    logging.config.dictConfig({
        'version': 1,
	    'disable_existing_loggers': True,
	    'formatters': {
		    'default': {'format': '[%(asctime)s] :: %(levelname)s :: %(module)s :: %(process)d :: %(thread)d :: %(message)s'}},
        'handlers': {
            'console': {
                'level': console_level,
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                # 'stream': 'ext://sys.stdout'
            },
            'file': {
                'level': file_level,
	             'mode': 'a+',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': log_path,
                'maxBytes': 1024 * 1024,
                'backupCount': 9
            }
        },
        'loggers': {
            'default': {
                'level': 'DEBUG',
                'handlers': ['console', 'file']
            },
	        'uvicorn.error': {
		        'propagate': False,
		        'handlers': ['console']
	        },
	        'app': {
		        'handlers': ['console'],
		        'propagate': False,
		        'level': 'INFO'},
	        'hbmqtt': {
		        'handlers': ['console'],
		        'propagate': False,
		        'level': 'INFO'}
        }
    })

    return logging.getLogger(name)

def log_set(level):
	formatter = "[%(asctime)s] :: %(levelname)s :: %(name)s :: %(message)s"
	log_level = logging.getLevelName(level)
	logging.basicConfig(level=log_level, format=formatter)
	# 输出到文件
	if not os.path.exists("logs"):
		os.mkdir("logs")
	log = logging.getLogger()
	log_filenum = 9
	log_maxsize = 4
	fh = RotatingFileHandler('./logs/service.log', mode='a+', maxBytes=log_maxsize * 1024 * 1024,
	                         backupCount=log_filenum, delay=True)
	fh.setFormatter(logging.Formatter(formatter))
	log.addHandler(fh)
