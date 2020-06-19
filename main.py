#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
import ctypes
from helper import is_admin
import os, sys, platform, time
from pydantic import BaseModel
from cores.log import configure_logger
import uvicorn
from bases import app

# 设置日志输出级别，可自己重新定义log_set
alog = configure_logger('default', 'logs/service.log')



if __name__ == '__main__':
	if not is_admin():
		alog.info("当前用户不是管理员，将以管理员身份运行此程序")
		if sys.version_info[0] == 3:
			ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
		os._exit(0)
	else:
		# 使用 uvicorn 启动 API Server
		debug = False
		# if (platform.system() != "Linux"):
		# 	debug = True
		alog.info("当前工作路径：{0} ,启动参数:debug={1}".format(str(os.getcwd()), str(debug)))
		if os.access(os.getcwd() + r'\vnet\tincd.exe', os.F_OK) and os.access(os.getcwd() + r'\vnet\_npc\npc.exe', os.F_OK):
			filename, extension = os.path.splitext(os.path.basename(__file__))
			appStr = filename + ':app'
			alog.info("Staring Service!!")
			if debug:
				uvicorn.run(appStr, host="127.0.0.1", port=8086, reload=debug, log_level="info")
			else:
				uvicorn.run(app, host="127.0.0.1", port=8086, reload=debug, log_level="info")
		else:
			alog.info("Dependent application is nonexistent, Stopping Service and Exit !!!!")
