#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
import time
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from helper import to_dict, success, failure, APPCtrl, is_ipv4, urlCheck
from cores.mqttc.pubc import MQTTStreamPubBase
from apps.vnet import api
from apps.vnet.pub import MQTTPub
from apps.vnet.manager import Manager

appname = "vnet"

APIHandler = APIRouter()
APIHandler.Pub = MQTTPub(appname)
APIHandler.Sub = MQTTStreamPubBase(appname, api)
APIHandler.Manager = Manager(appname, APIHandler.Pub)


class pingItem(BaseModel):
	id: str = None


class stopItem(BaseModel):
	id: str = None


class gateItem(BaseModel):
	gate: str
	auth_code: str = None
	id: str = None

class actionItem(BaseModel):
	gate: str
	action: str
	auth_code: str = None
	id: str = None

class vnetItem(BaseModel):
	host: str
	user: str
	gate: str
	local_ip: str = None
	dest_ip: str = None
	auth_code: str = None
	id: str = None


@APIHandler.on_event("startup")
async def startup():
	APIHandler.Pub.start()
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
	ret = APIHandler.Manager.enable_heartbeat(True, 60)
	if ret:
		return success(id, ret)
	else:
		return failure(id, "error")


@APIHandler.get("/tunnel")
def api_npstunnel(params):
	if not type(params) is dict:
		params = to_dict(params)
	id = params.get("id") or uuid.uuid1()
	host = params.get("host")
	user = params.get("user")
	ret, ret_content = None, None
	if host and user:
		if not urlCheck(host).result():
			return failure(id, "host must be domain or ipv4 or url")
		else:
			APIHandler.Manager.nps_host = urlCheck(host).result()
			APIHandler.Manager.userinfo['name'] = user
			APIHandler.Manager.userinfo['tunnel_host'] = host
			ret, ret_content = APIHandler.Manager.nps_tunnel()
	else:
		ret_content = "params lost  host or user"
	if ret:
		return success(id, ret_content)
	else:
		return failure(id, ret_content)


@APIHandler.post("/ready")
def api_ready(params: gateItem):
	if not type(params) is dict:
		params = params.dict()
	# print(json.dumps(params, sort_keys=True, indent=4, separators=(',', ':')))
	id = params.get("id") or uuid.uuid1()
	auth_code = params.get("auth_code") or APPCtrl().get_accesskey()
	if auth_code:
		APIHandler.Manager.TRAccesskey = auth_code
	else:
		return failure(id, "params lost  auth_code")
	ret, ret_content = APIHandler.Manager.vnet_ready(params.get("gate"))
	if ret:
		return success(id, ret_content)
	else:
		return failure(id, ret_content)


@APIHandler.post("/action")
def api_action(params: actionItem):
	if not type(params) is dict:
		params = params.dict()
	# print(json.dumps(params, sort_keys=True, indent=4, separators=(',', ':')))
	id = params.get("id") or uuid.uuid1()
	auth_code = params.get("auth_code") or APPCtrl().get_accesskey()
	if auth_code:
		APIHandler.Manager.TRAccesskey = auth_code
	else:
		return failure(id, "params lost  auth_code")
	gate = params.get("gate")
	action = params.get("action")
	if action not in ["install", "uninstall", "start", "stop", "upgrade"]:
		return failure(id, "action is unsupported")
	ret, ret_content = APIHandler.Manager.vnet_action(gate, action)
	if ret:
		return success(id, ret_content)
	else:
		return failure(id, ret_content)


@APIHandler.get("/status")
def api_status():
	id = str(time.time())
	ret, ret_content = None, None
	ret, ret_content = APIHandler.Manager.vnet_status()
	if ret:
		return success(id, ret_content)
	else:
		return failure(id, ret_content)


@APIHandler.post("/start")
def api_start(params: vnetItem):
	if not type(params) is dict:
		params = params.dict()
	# print(json.dumps(params, sort_keys=True, indent=4, separators=(',', ':')))
	id = params.get("id") or uuid.uuid1()
	host = params.get("host")
	user = params.get("user")
	gate = params.get("gate")
	ret, ret_content = None, None
	if host and user and gate:
		if not urlCheck(host).result():
			return failure(id, "host must be domain or ipv4 or url")
		else:
			vret, vret_content = APIHandler.Manager.vnet_status()
			if vret:
				str = "用户 {0} 正在使用中……，如需重新配置，请先停止再启动".format(vret_content.userinfo.get("name"))
				return failure(id, str)
			else:
				auth_code = params.get("auth_code") or APPCtrl().get_accesskey()
				if auth_code:
					APIHandler.Manager.TRAccesskey = auth_code
				else:
					return failure(id, "params lost  auth_code")
				if params.get("local_ip"):
					if is_ipv4(params.get("local_ip")):
						APIHandler.Manager.userinfo['local_vnet_ip'] = params.get("local_ip")
				if params.get("dest_ip"):
					if is_ipv4(params.get("dest_ip")):
						APIHandler.Manager.userinfo['dest_ip'] = params.get("dest_ip")
				APIHandler.Manager.nps_host = urlCheck(host).result()
				APIHandler.Manager.userinfo['name'] = user
				APIHandler.Manager.userinfo['tunnel_host'] = host
				APIHandler.Manager.userinfo['gate'] = gate
				ret, ret_content = APIHandler.Manager.start_vnet()
	else:
		ret_content = "params lost  host or user or gate"
	if ret:
		return success(id, ret_content)
	else:
		return failure(id, ret_content)


@APIHandler.post("/stop")
def api_stop(params: stopItem):
	if not type(params) is dict:
		params = params.dict()
	# print(json.dumps(params, sort_keys=True, indent=4, separators=(',', ':')))
	id = params.get("id") or uuid.uuid1()
	ret, ret_content = APIHandler.Manager.stop_vnet()
	if ret:
		return success(id, ret_content)
	else:
		return failure(id, ret_content)
