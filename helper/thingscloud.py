#!/usr/bin/python
# -*- coding: UTF-8 -*-
import requests
import json
import time


class CloudApiv1:
	def __init__(self, Accesskey=None):
		self.__Authcode = Accesskey or "viccom@@dongbala"  # 密钥（长度必须为16、24、32）
		self.__url = 'http://ioe.thingsroot.com/api/method'

	def get_gate_list(self):
		url = self.__url + '/iot_ui.iot_api.devices_list?filter=online'
		headers = {'AuthorizationCode': self.__Authcode, 'Accept': 'application/json'}
		# print("@@@@@@@@@@@@@@", self.__Authcode)
		r = requests.post(url, headers=headers)
		ret_content = None
		if r.status_code == 200:
			ret_content = r.json().get('message')
		return ret_content

	def get_gate_status(self, sn):
		url = self.__url + '/iot.device_api.device_status?sn=' + sn
		headers = {'AuthorizationCode': self.__Authcode, 'Accept': 'application/json'}
		# print("@@@@@@@@@@@@@@", self.__Authcode)
		r = requests.post(url, headers=headers)
		ret_content = None
		if r.status_code == 200:
			ret_content = r.json()
		return ret_content

	def get_gate_apps(self, sn):
		url = self.__url + '/iot.user_api.device_app_list?sn=' + sn
		headers = {'AuthorizationCode': self.__Authcode, 'Accept': 'application/json'}
		r = requests.get(url, headers=headers)
		ret_content = None
		if r.status_code == 200:
			ret_content = r.json()
		return ret_content

	def get_device_data(self, sn, devsn):
		url = self.__url + '/iot.user_api.device_data?sn=' + sn + "&vsn=" + devsn
		headers = {'AuthorizationCode': self.__Authcode, 'Accept': 'application/json'}
		r = requests.post(url, headers=headers)
		ret_content = None
		if r.status_code == 200:
			ret_content = r.json()
		return ret_content

	def action_send_app(self, action, action_data):
		action_url = {
			"install": self.__url + '/iot.device_api.app_install',
			"start": self.__url + '/iot.device_api.app_start',
			"stop": self.__url + '/iot.device_api.app_stop',
			"uninstall": self.__url + '/iot.device_api.app_uninstall',
			"upgrade": self.__url + '/iot.device_api.app_upgrade',
		}
		ret_content = None
		if action_url.get(action):
			headers = {'AuthorizationCode': self.__Authcode, 'Content-Type': 'application/json'}
			r = requests.post(action_url.get(action), headers=headers, data=json.dumps(action_data))
			if r.status_code == 200:
				ret_content = r.json()
		return ret_content

	def action_send_command(self, send_data):
		url = self.__url + '/iot.device_api.send_command'
		headers = {'AuthorizationCode': self.__Authcode, 'Content-Type': 'application/json'}
		r = requests.post(url, headers=headers, data=json.dumps(send_data))
		# print("action_send_output:: ", r)
		ret_content = None
		if r.status_code == 200:
			ret_content = r.json()
		return ret_content

	def action_send_output(self, send_data):
		url = self.__url + '/iot.device_api.send_output'
		headers = {'AuthorizationCode': self.__Authcode, 'Content-Type': 'application/json'}
		r = requests.post(url, headers=headers, data=json.dumps(send_data))
		# print("action_send_output:: ", r)
		ret_content = None
		if r.status_code == 200:
			ret_content = r.json()
		return ret_content

	def get_action_result(self, id):
		url = self.__url + '/iot.device_api.get_action_result?id=' + id
		headers = {'AuthorizationCode': self.__Authcode, 'Accept': 'application/json'}
		r = requests.get(url, headers=headers)
		# print("get_action_result:: ", r)
		ret_content = None
		if r.status_code == 200:
			ret_content = r.json()
		return ret_content

	def post_to_cloud(self, data):
		rand_id = data['id']
		action_result = {}
		send_ret = self.action_send_output(data)
		# print("***********************", send_ret)
		if send_ret:
			action_ret = None
			action_result["cloud_mes"] = send_ret
			if send_ret['message'] == rand_id:
				for i in range(4):
					action_ret = self.get_action_result(rand_id)
					if action_ret:
						break
					time.sleep(i + 1)
			# print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&", action_ret)
			if action_ret:
				action_result["gate_mes"] = action_ret["message"]
				return True, action_result
			else:
				action_result["gate_mes"] = 'gate has no response !'
				return False, action_result
		else:
			action_result["cloud_mes"] = 'cloud has no response !'
			return False, action_result

	def post_action_to_app(self, action, data):
		rand_id = data['id']
		action_result = {}
		send_ret = self.action_send_app(action, data)
		if send_ret:
			action_ret = None
			action_result["cloud_mes"] = send_ret
			if send_ret['message'] == rand_id:
				for i in range(4):
					action_ret = self.get_action_result(rand_id)
					if action_ret:
						break
					time.sleep(i + 1)
			# print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&", action_ret)
			if action_ret:
				action_result["gate_mes"] = action_ret["message"]
				return True, action_result
			else:
				action_result["gate_mes"] = 'gate has no response !'
				return False, action_result
		else:
			action_result["cloud_mes"] = 'cloud has no response !'
			return False, action_result

	def post_command_to_cloud(self, data):
		rand_id = data['id']
		action_result = {}
		send_ret = self.action_send_command(data)
		# print("***********************", send_ret)
		if send_ret:
			action_ret = None
			action_result["cloud_mes"] = send_ret
			if send_ret['message'] == rand_id:
				for i in range(4):
					action_ret = self.get_action_result(rand_id)
					if action_ret:
						break
					time.sleep(i + 1)
			# print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&", action_ret)
			if action_ret:
				action_result["gate_mes"] = action_ret["message"]
				return True, action_result
			else:
				action_result["gate_mes"] = 'gate has no response !'
				return False, action_result
		else:
			action_result["cloud_mes"] = 'cloud has no response !'
			return False, action_result

	def gate_enable_data_one_short(self, gate):
		send_data = {"id": str(time.time()), "device": gate, "data": 300}
		url = self.__url + '/iot.device_api.sys_enable_data_one_short'
		headers = {'AuthorizationCode': self.__Authcode, 'Content-Type': 'application/json'}
		r = requests.post(url, headers=headers, data=json.dumps(send_data))
		ret_content = None
		if r.status_code == 200:
			ret_content = r.json()
		return ret_content
