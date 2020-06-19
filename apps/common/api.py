#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
import os
import base64
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from helper import to_dict, success, failure, APPCtrl
from cores.mqttc.pubc import MQTTStreamPubBase
from configparser import ConfigParser
from apps.common.manager import Manager
from apps.common import api


appname = "common"

APIHandler = APIRouter()
APIHandler.Sub = MQTTStreamPubBase(appname, api)
APIHandler.Manager = Manager(appname)


class pingItem(BaseModel):
	data: dict
	id: str = None


class configItem(BaseModel):
	npshost: str
	npsuser:str
	gate: str
	auth_code: str
	id: str = None



@APIHandler.on_event("startup")
async def startup():
	APIHandler.Sub.start()
	APIHandler.Manager.start()
	pass


@APIHandler.on_event("shutdown")
async def shutdown():
	pass


@APIHandler.post("/ping")
def api_ping(params: pingItem):
	if not type(params) is dict:
		params = params.dict()
	id = params.get("id") or uuid.uuid1()
	ret = params
	if ret:
		return success(id, params)
	else:
		return failure(id, "error")



@APIHandler.get("/load")
def api_load(params):
	if not type(params) is dict:
		params = to_dict(params)
	id = params.get("id") or uuid.uuid1()
	npshost = None
	npsuser = None
	gate = None
	auth_code = None
	config = ConfigParser()
	if os.access(os.getcwd() + '\\config.ini', os.F_OK):
		config.read('config.ini')
		if config.has_option('thingscloud', 'npshost'):
			npshost = config.get('thingscloud', 'npshost')
		if config.has_option('thingscloud', 'npsuser'):
			npsuser = config.get('thingscloud', 'npsuser')
		if config.has_option('thingscloud', 'gate'):
			gate = config.get('thingscloud', 'gate')
		if config.has_option('thingscloud', 'accesskey'):
			if len(config.get('thingscloud', 'accesskey')) == 48:
				auth_code = base64.b64decode(config.get('thingscloud', 'accesskey').encode()).decode()
	else:
		return None
	ret = {"npshost": npshost, "npsuser": npsuser, "gate": gate, "auth_code": auth_code}
	if ret:
		return success(id, ret)
	else:
		return failure(id, "error")


@APIHandler.post("/save")
def api_save(params: configItem):
	if not type(params) is dict:
		params = params.dict()
	id = params.get("id") or uuid.uuid1()
	npshost = params.get("npshost")
	npsuser = params.get("npsuser")
	gate = params.get("gate")
	accesskey = params.get("auth_code")
	if len(accesskey) == 36:
		accesskey = base64.b64encode(accesskey.encode()).decode()
		config = ConfigParser()
		if os.access(os.getcwd() + '\\config.ini', os.F_OK):
			config.read('config.ini')
			if not config.has_section("thingscloud"):
				config.add_section("thingscloud")
			print("@@@@@@@@@@@", npshost, npsuser, gate, accesskey)
			if npshost:
				config.set("thingscloud", 'npshost', npshost)
			else:
				config.remove_option("thingscloud", 'npshost')
			if npsuser:
				config.set("thingscloud", 'npsuser', npsuser)
			else:
				config.remove_option("thingscloud", 'npsuser')
			if gate:
				config.set("thingscloud", 'gate', gate)
			else:
				config.remove_option("thingscloud", 'gate')
			config.set("thingscloud", 'accesskey', accesskey)
			config.write(open('config.ini', 'w'))
		else:
			config.read('config.ini')
			config.add_section("thingscloud")
			if npshost:
				config.set("thingscloud", 'npshost', npshost)
			if npsuser:
				config.set("thingscloud", 'npsuser', npsuser)
			if gate:
				config.set("thingscloud", 'gate', gate)
			config.set("thingscloud", 'accesskey', accesskey)
			config.write(open('config.ini', 'w'))
		return success(id, "ok")
	else:
		return failure(id, "auth_code is error")


@APIHandler.delete("/remove")
def api_remove(params):
	if not type(params) is dict:
		params = params.dict()
	id = params.get("id") or uuid.uuid1()
	config = ConfigParser()
	if os.access(os.getcwd() + '\\config.ini', os.F_OK):
		config.read('config.ini')
		config.remove_section("thingscloud")
		config.write(open('config.ini', 'w'))
		return success(id, "ok")
	else:
		return failure(id, "config.ini does not exist")

@APIHandler.get("/gatelist")
def api_gatelist(params):
	if not type(params) is dict:
		params = to_dict(params)
	# print(json.dumps(params, sort_keys=True, indent=4, separators=(',', ':')))
	id = params.get("id") or uuid.uuid1()
	auth_code = params.get("auth_code") or APPCtrl().get_accesskey()
	if auth_code:
		APIHandler.Manager.TRAccesskey = auth_code
	else:
		return failure(id, "params lost  auth_code")
	ret = APIHandler.Manager.gatelist()
	if ret:
		return success(id, ret)
	else:
		return failure(id, "error")


@APIHandler.get("/online")
def api_online(params):
	if not type(params) is dict:
		params = to_dict(params)
	# print(json.dumps(params, sort_keys=True, indent=4, separators=(',', ':')))
	id = params.get("id") or uuid.uuid1()
	if not params.get("gate"):
		return failure(id, "params lost  gate")
	auth_code = params.get("auth_code") or APPCtrl().get_accesskey()
	if auth_code:
		APIHandler.Manager.TRAccesskey = auth_code
	else:
		return failure(id, "params lost  auth_code")
	ret = APIHandler.Manager.online(params.get("gate"))
	if ret:
		return success(id, "ONLINE")
	else:
		return failure(id, "OFFLINE")
