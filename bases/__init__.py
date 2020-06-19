#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
import os
import base64
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from pydantic import BaseModel
from starlette.responses import FileResponse, RedirectResponse, PlainTextResponse
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from cores.mqttbroker import MQTTBroker
import importlib
from conf import serivces
from cores.log import log_set, configure_logger
from configparser import ConfigParser


class authItem(BaseModel):
	auth_code: str


def get_application() -> FastAPI:
	if not os.path.exists("logs"):
		os.mkdir("logs")
	# 定义API服务，可指定openapi_url和docs_url路径
	application = FastAPI()
	# app = FastAPI(openapi_url="/v1/api/openapi.json", docs_url="/v1/api/docs")

	templates = Jinja2Templates(directory="html")
	application.mount('/static', StaticFiles(directory='html/static'), name='static')
	application.broker = MQTTBroker()

	# 在根目录的conf.py文件serivces中定义使用的模块服务名称（是且必须是模块的目录名）
	for m in serivces:
		service_module = importlib.import_module('apps.{0}.app'.format(m))
		api = service_module.init(m)
		application.include_router(api, prefix='/v1/' + m + '/api', tags=[m])
	application.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	@application.on_event("startup")
	async def startup():
		# 启动MQTTBroker
		# formatter = logging.Formatter(
		# 	"[%(asctime)s] :: %(levelname)s :: %(module)s :: %(process)d :: %(thread)d :: %(message)s",
		# 	"%Y-%m-%d %H:%M:%S")
		# handler = logging.StreamHandler()
		# handler.setLevel(logging.DEBUG)
		# handler.setFormatter(formatter)
		# # 为日志器logger添加上面创建的处理器handler
		# fastapi_logger.addHandler(handler)
		alog = configure_logger('default', 'logs/service.log')
		alog.info('****************** Starting hbmqtt Server *****************')
		alog.info("Staring hbmqtt broker..")
		application.broker.start()
		pass

	@application.on_event("shutdown")
	async def shutdown():
		pass

	@application.get("/")
	async def index(request: Request):
		# print(request.body())
		return templates.TemplateResponse('vnet.html', {'request': request})
	# async def index():
	# 	return PlainTextResponse('Micro Service is running\n')

	@application.get("/vnet")
	async def index(request: Request):
		# print(request.body())
		return templates.TemplateResponse('vnet.html', {'request': request})

	@application.get("/vserial")
	async def index(request: Request):
		# print(request.body())
		return templates.TemplateResponse('vserial.html', {'request': request})

	@application.post("/authcode")
	async def authcode(params: authItem):
		if not type(params) is dict:
			params = params.dict()
		accesskey = params.get("auth_code")
		if len(accesskey) == 36:
			accesskey = base64.b64encode(accesskey.encode()).decode()
			config = ConfigParser()
			if os.access(os.getcwd() + '\\config.ini', os.F_OK):
				config.read('config.ini')
				if config.has_option('thingscloud', 'accesskey'):
					config.set("thingscloud", 'accesskey', accesskey)
					config.write(open('config.ini', 'w'))
			else:
				config.read('config.ini')
				config.add_section("thingscloud")
				config.set("thingscloud", 'accesskey', accesskey)
				config.write(open('config.ini', 'w'))
			return {"result": True, "data": "ok"}
		else:
			return {"result": False, "data": "auth_code is error"}

	return application


app = get_application()
