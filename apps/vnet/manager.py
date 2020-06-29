import threading
import logging
import os
import re
import json
import random
import time
import wmi
import pythoncom
import winreg
import hashlib
import win32serviceutil
from cores.log import log_set, configure_logger
from ping3 import ping
from conf import nps_allowed_ports
from helper import is_ipv4, APPCtrl
from helper.npsManager import npsCryp, npsApiv1
from helper.thingscloud import CloudApiv1


class Manager(threading.Thread):
	def __init__(self, appname, stream_pub):
		threading.Thread.__init__(self)
		self.TRAccesskey = None
		self.TRCloudapi = None
		self.nps_host = None
		self.NPSApi = None
		self.userinfo = {"name": None, "gate": None, "cid": None, "vkey": None, "client_status": None, "client_online": None,
            "tunnel_alias": None, "tid": None, "tunnel_host": None, "tunnel_port": None, "tunnel_Target": "127.0.0.1:665",
            "tunnel_status": None, "tunnel_online": None, "gate_lan_ip": None, "gate_lan_netmask": None, "dest_ip": None,
            "local_vnet_ip": None, "gate_status": None, "gate_vpn_status": None, "gate_vpn_config": None}
		self._dest_services = ["Npc", "tinc.vnetbridge"]
		self._services_status = {}
		self.__auth_key = None
		self._gate_online = False
		self._gate_vpn_is_running = False
		self._service_is_running = False
		self._vnet_is_running = False
		self._result = {}
		self._handlers = []
		self._start_time = None
		self._stop_time = None
		self._enable_heartbeat = APPCtrl().get_heartbeat()
		self._heartbeat_timeout = time.time() + 90
		self._thread_stop = False
		self._appname = appname
		self._mqtt_pub = stream_pub
		self._log = configure_logger('default', 'logs/service.log')

	def nps_changevk(self):
		if self.userinfo['vkey']:
			self._log.info("{0} 生成新的Npc服务".format(self.userinfo['name']))
			npcbinpath = os.getcwd() + r"\vnet\_npc\npc.exe"
			npcinscmd = ['sc stop Npc', npcbinpath + ' install -server=' + self.userinfo['tunnel_host'] + ':7088' + ' -vkey=' + self.userinfo['vkey'],
			             'sc config Npc start= demand']
			for cmd in npcinscmd:
				os.popen(cmd)
				time.sleep(0.05)

	def check_tinc_service(self):
		rRoot = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
		subDir = r'Software\tinc'
		curpath = os.getcwd()
		tincbinpath = os.getcwd() + r"\vnet"
		npcbinpath = curpath + r"\vnet\_npc\npc.exe"
		tincinscmd = ['sc stop tinc.vnetbridge', 'sc delete tinc.vnetbridge',
		              tincbinpath + r'\tincd.exe -n ' + 'vnetbridge', 'sc stop tinc.vnetbridge',
		              'sc config tinc.vnetbridge start= demand']
		npcinscmd = ['sc stop Npc', npcbinpath + ' install -server=nps.dongbala.top:7088 -vkey=dongwk@dongbala.top',
		             'sc config Npc start= demand', 'sc stop Npc']
		keyHandle = None
		try:
			keyHandle = winreg.OpenKey(rRoot, subDir)
		except Exception as ex:
			self._log.error(subDir + " 不存在")
		if not keyHandle:
			keyHandle = winreg.CreateKey(rRoot, subDir)
		if keyHandle:
			count = winreg.QueryInfoKey(keyHandle)[1]  # 获取该目录下所有键的个数(0-下属键个数;1-当前键值个数)
			if not count:
				self._log.info("创建 tinc path:: {0}".format(tincbinpath))
				winreg.SetValue(rRoot, subDir, winreg.REG_SZ, tincbinpath)
				for cmd in tincinscmd:
					os.popen(cmd)
					time.sleep(0.1)
				# for cmd in npcinscmd:
				# 	os.popen(cmd)
				# 	time.sleep(0.1)
				# ret1 = os.popen('sc qc tinc.vnetbridge|findstr "BINARY_PATH_NAME"').read().strip()
				# ret2 = os.popen('sc qc npc|findstr "BINARY_PATH_NAME"').read().strip()
				# print(ret1, '\r\n', ret2)
			else:
				name, key_value, value_type = winreg.EnumValue(keyHandle, 0)
				if tincbinpath not in key_value:
					self._log.info("修改 tinc path:: {0}".format(tincbinpath))
					winreg.SetValue(rRoot, subDir, winreg.REG_SZ, tincbinpath)
					for cmd in tincinscmd:
						os.popen(cmd)
						time.sleep(0.1)
		try:
			win32serviceutil.QueryServiceStatus('tinc.vnetbridge')
		except Exception as ex:
			for cmd in tincinscmd:
				os.popen(cmd)
				time.sleep(0.1)


	@staticmethod
	def wmi_in_thread(myfunc, *args, **kwargs):
		pythoncom.CoInitialize()
		try:
			c = wmi.WMI()
			return myfunc(c, *args, **kwargs)
		finally:
			pythoncom.CoUninitialize()

	@staticmethod
	def prepend_tap(wmiService, dAdapter, ipaddr, subnet):
		destnic = None
		TAP_Windows_Nics = wmiService.Win32_NetworkAdapter(Manufacturer="TAP-Windows Provider V9")
		if len(TAP_Windows_Nics) > 0:
			for tap_nic in TAP_Windows_Nics:
				if tap_nic.NetConnectionID == "vnet":
					tap_nic.disable
					time.sleep(0.5)
					tap_nic.enable
					destnic = tap_nic.GUID
					# print(tap_nic.Manufacturer)
					# print(tap_nic.GUID)
					# print(tap_nic.NetConnectionID)
					# print(tap_nic.NetEnabled)
					# print(tap_nic.ServiceName)
					# print(tap_nic.ProductName)
					break
			if not destnic:
				TAP_Windows_Nics[0].NetConnectionID = dAdapter
				TAP_Windows_Nics[0].disable
				time.sleep(1)
				TAP_Windows_Nics[0].enable
				destnic = TAP_Windows_Nics[0].GUID
		else:
			logging.error('NO TAP-Windows!')
		if destnic:
			colNicConfigs = wmiService.Win32_NetworkAdapterConfiguration(IPEnabled=False, ServiceName="tap0901",
			                                                             SettingID=destnic)
			if len(colNicConfigs) < 1:
				return False
			else:
				Adapter1 = colNicConfigs[0]
				RetVal = Adapter1.EnableStatic(ipaddr, subnet)
				# print("ok", ipaddr, subnet)
				return True
		else:
			return False

	@staticmethod
	def check_ip_alive(dest_ip):
		ret = ping(dest_ip, unit='ms', timeout=2)
		if ret:
			return {'message': dest_ip + ' online', "delay": str(int(ret)) + 'ms'}
		else:
			return {'message': dest_ip + ' offline', "delay": 'timeout'}

	def nps_authcode(self):
		if not self.NPSApi:
			self.NPSApi = npsApiv1(self.nps_host)
		naes = npsCryp()
		retkey = self.NPSApi.nps_api_get("/auth/getauthkey")
		if retkey:
			self.__auth_key = naes.decrypt(retkey.get(
				"crypt_auth_key"))  # now_time = str(int(time.time()))  # auth_key_md5 = hashlib.md5((auth_key + now_time).encode(encoding="UTF-8")).hexdigest()
		return self.__auth_key

	def nps_tunnel_status(self):
		if not self.NPSApi:
			self.NPSApi = npsApiv1(self.nps_host)
		if not self.__auth_key:
			self.nps_authcode()
		if self.__auth_key:
			if self.userinfo['tid']:
				now_time = str(int(time.time()))
				auth_key_md5 = hashlib.md5((self.__auth_key + now_time).encode(encoding="UTF-8")).hexdigest()
				tunnel = self.NPSApi.nps_api_post("/index/getonetunnel/",
				                                   {"auth_key": auth_key_md5, "timestamp": now_time, "id": self.userinfo['tid']})
				if tunnel:
					if tunnel.get("data"):
						self.userinfo['client_online'] = tunnel.get("data").get("Client").get("IsConnect")
					# print(tunnel)


	def nps_tunnel(self):
		if not self.NPSApi:
			self.NPSApi = npsApiv1(self.nps_host)
		if not self.__auth_key:
			self.nps_authcode()
		if self.__auth_key:
			used_ports = [nps_allowed_ports[0]]
			now_time = str(int(time.time()))
			auth_key_md5 = hashlib.md5((self.__auth_key + now_time).encode(encoding="UTF-8")).hexdigest()
			clients = self.NPSApi.nps_api_post("/client/list",
			                       {"auth_key": auth_key_md5, "timestamp": now_time, "start": 0, "limit": 100}).get(
				"rows")
			if clients:
				for c in clients:
					if c.get("Remark") == self.userinfo['name']:
						# print("@@@@@@@@@", c.get("Remark"), self.userinfo['name'])
						self.userinfo['cid'] = c.get("Id")
						self.userinfo['vkey'] = c.get("VerifyKey")
						break
				if self.userinfo['cid']:
					tunnels = self.NPSApi.nps_api_post("/index/gettunnel/",
					                       {"auth_key": auth_key_md5, "timestamp": now_time, "client_id": None,
					                        "type": "tcp", "start": 0, "limit": 100}).get("rows")
					if tunnels:
						for t in tunnels:
							if not t.get("Port") in used_ports:
								used_ports.append(t.get("Port"))
							if t.get("Target").get("TargetStr") == self.userinfo['tunnel_Target'] and t.get("Client").get("Remark") == self.userinfo['name']:
								# print(json.dumps(t, sort_keys=False, indent=4, separators=(',', ':')))
								self.userinfo['tid'] = t.get("Id")
								self.userinfo['client_status'] = t.get("Client").get("Status")
								self.userinfo['client_online'] = t.get("Client").get("IsConnect")
								self.userinfo['tunnel_status'] = t.get("Status")
								self.userinfo['tunnel_online'] = t.get("RunStatus")
								self.userinfo['tunnel_alias'] = t.get("Remark")
								self.userinfo['tunnel_port'] = t.get("Port")
								break
					if not self.userinfo['tid']:
						used_ports.sort()
						newPort = 0
						for x in range(0, 5):
							newPort = used_ports[0] + len(used_ports) + x
							if not newPort in used_ports:
								break
						newTunnel = {"auth_key": auth_key_md5, "timestamp": now_time, "client_id": self.userinfo['cid'],
						             "type": "tcp", "remark": self.userinfo['name'] + "_vnet_npc_proxy",
						             "port": newPort, "target": "127.0.0.1:665"}
						self._log.info("{0} 增加新隧道 {1}".format(self.userinfo.get("name"), newPort))
						ret = self.NPSApi.nps_api_post("/index/add/", newTunnel)
						tunnels = self.NPSApi.nps_api_post("/index/gettunnel/",
						                       {"auth_key": auth_key_md5, "timestamp": now_time,
						                        "client_id": self.userinfo['cid'], "type": "tcp", "start": 0,
						                        "limit": 100}).get("rows")
						if tunnels:
							for t in tunnels:
								if not t.get("Port") in used_ports:
									used_ports.append(t.get("Port"))
								if t.get("Target").get("TargetStr") == self.userinfo['tunnel_Target'] and t.get("Client").get("Remark") == self.userinfo['name']:
									# print(json.dumps(t, sort_keys=False, indent=4, separators=(',', ':')))
									self.userinfo['tid'] = t.get("Id")
									self.userinfo['client_status'] = t.get("Client").get("Status")
									self.userinfo['client_online'] = t.get("Client").get("IsConnect")
									self.userinfo['tunnel_status'] = t.get("Status")
									self.userinfo['tunnel_online'] = t.get("RunStatus")
									self.userinfo['tunnel_alias'] = t.get("Remark")
									self.userinfo['tunnel_port'] = t.get("Port")
									break
				else:
					self._log.warning("NPS用户 {0} 不存在".format(self.userinfo.get("name")))
			return True, self.userinfo
		else:
			self._log.warning("访问 NPS 异常")
			return False, "访问 NPS 异常"

	def service_status(self):
		# 检测本次服务是否运行
		for s in self._dest_services:
			cmd1 = 'sc query ' + s + '|find /I "STATE"'
			cmd_ret = os.popen(cmd1).read().strip()
			cmd_ret = re.split('\s+', cmd_ret)
			if len(cmd_ret) > 1:
				self._services_status[s] = cmd_ret[3]
		for val in self._services_status.values():
			if val != "RUNNING":
				self._service_is_running = False
				break
			else:
				self._service_is_running = True

	def services_start(self):
		if not self._service_is_running:
			services_start = 0
			for s in self._dest_services:
				time.sleep(1)
				cmd1 = 'sc start ' + s + '|find /I "STATE"'
				cmd_ret = os.popen(cmd1).read().strip()
				if cmd_ret:
					self._log.info(s + ' is starting!')
					services_start = services_start + 1
				else:
					self._log.error(s + ' start failed! please retry!')
			if services_start == 2:
				self._service_is_running = True
				return True
			else:
				return False
		else:
			return True

	def services_stop(self):
		self._stop_time = time.time()
		services_is_stop = True
		for val in self._services_status.values():
			if val == "RUNNING":
				services_is_stop = False
		if not services_is_stop:
			print("################## stopping services ################## ")
			services_sop = 0
			for s in self._dest_services:
				cmd1 = 'sc stop ' + s + '|find /I "STATE"'
				cmd_ret = os.popen(cmd1).read().strip()
				time.sleep(0.1)
				if cmd_ret:
					self._log.info(s + ' is stopping!')
					services_sop = services_sop + 1
					time.sleep(1)
				else:
					self._log.error(s + ' stop failed!! please retry!')
			if services_sop == 2:
				self._service_is_running = False
				return True
			else:
				return False
		else:
			return True

	def gate_vpn_data(self):
		data = self.TRCloudapi.get_device_data(self.userinfo['gate'], self.userinfo['gate'] + ".freeioe_Vnet_npc")
		if data:
			try:
				rawdata = data['message']
				# print(json.dumps(rawdata, sort_keys=False, indent=4, separators=(',', ':')))
				if rawdata:
					gate_lan_ip = rawdata.get("lan_ip").get("PV")
					if gate_lan_ip and is_ipv4(gate_lan_ip):
						local_vnet_ip = ".".join(gate_lan_ip.split(".")[0:3]) + "." + str(random.randint(11, 244))
						if rawdata.get("bridge_run").get("PV") == "running":
							self.userinfo["gate_vpn_status"] = True
							self._gate_vpn_is_running = True
						else:
							self.userinfo["gate_vpn_status"] = False
							self._gate_vpn_is_running = False
						if rawdata.get("bridge_config").get("PV") != "":
							self.userinfo["gate_vpn_config"] = json.loads(rawdata.get("bridge_config").get("PV"))
						if not self.userinfo["gate_lan_ip"]:
							self.userinfo["gate_lan_ip"] = gate_lan_ip
							self.userinfo["gate_lan_netmask"] = rawdata.get("lan_netmask").get("PV")
						if not self.userinfo["local_vnet_ip"]:
							self.userinfo["local_vnet_ip"] = local_vnet_ip
						if not self.userinfo["dest_ip"]:
							self.userinfo["dest_ip"] = gate_lan_ip
			except Exception as ex:
				self._log.exception(ex)

	def start_vnet(self):
		if not self._vnet_is_running:
			self.check_tinc_service()
			if not self.TRCloudapi:
				self.TRCloudapi = CloudApiv1(self.TRAccesskey)
			self.enable_heartbeat(True, 60)
			if not self.NPSApi:
				self.NPSApi = npsApiv1(self.nps_host)
			if not self.__auth_key:
				self.nps_authcode()
			if not self.userinfo['tid']:
				# print("get tid")
				self.nps_tunnel()
			if self.userinfo['tid']:
				now_time = str(int(time.time()))
				auth_key_md5 = hashlib.md5((self.__auth_key + now_time).encode(encoding="UTF-8")).hexdigest()
				if not self.userinfo['client_status']:
					# print("用户 {0} 当前禁用".format(self.userinfo["name"]))
					ret = self.NPSApi.nps_api_post("/client/changestatus/",
					                   {"auth_key": auth_key_md5, "timestamp": now_time, "id": self.userinfo['cid'],
					                    "status": 1})
				if not self.userinfo['tunnel_status']:
					# print("隧道 {0} 当前禁用".format(self.userinfo["tunnel_alias"]))
					ret = self.NPSApi.nps_api_post("/index/start/",
					                   {"auth_key": auth_key_md5, "timestamp": now_time, "id": self.userinfo['tid']})
				# 检测网关是否在线
				gate_status_ret = self.TRCloudapi.get_gate_status(self.userinfo['gate'])
				if gate_status_ret:
					if gate_status_ret['message'] == "ONLINE":
						self._gate_online = True
						self.userinfo['gate_status'] = "ONLINE"
					else:
						self._gate_online = False
						self.userinfo['gate_status'] = "OFFLINE"
				if self._gate_online:
					self.gate_vpn_data()
					local_vnet_ip = self.userinfo["local_vnet_ip"]
					local_vnet_netmask = self.userinfo["gate_lan_netmask"]
					if local_vnet_ip and is_ipv4(local_vnet_ip):
						self.nps_changevk()
						time.sleep(0.5)
						self.wmi_in_thread(self.prepend_tap, "vnet", [local_vnet_ip], ["255.255.255.0"])
						self.services_start()
						gate_vnet_config = {"net": "bridge", "Address": self.userinfo['tunnel_host'],
						                    "Port": str(self.userinfo['tunnel_port']), "proxy_name": "vnet_npc_proxy",
						                    "user_id": self.userinfo['name']}
						gate_datas = {"id": self.userinfo['gate'] + '/send_command/start/' + str(time.time()),
						              "device": self.userinfo['gate'],
						              "data": {"device": self.userinfo['gate'] + ".freeioe_Vnet_npc", "cmd": "start",
						                       "param": gate_vnet_config}}
						ret, ret_content = self.TRCloudapi.post_command_to_cloud(gate_datas)
						# print(json.dumps(ret, sort_keys=False, indent=4, separators=(',', ':')))
						if ret:
							if ret_content["gate_mes"]["result"]:
								self._vnet_is_running = True
								self._start_time = time.time()
								return self._vnet_is_running, self.userinfo
							else:
								self.services_stop()
								self.clean_cfg()
								return False, "下发指令到网关不正常，请检查后重试"
						else:
							self.services_stop()
							self.clean_cfg()
							return False, "网关VPN服务启动不正常，请检查后重试"
					else:
						self.services_stop()
						self.clean_cfg()
						return False, "无法获取正确的本地Vnet IP，网关可能未安装应用，或未开启数据上传，请检查后重试"
				else:
					self.services_stop()
					self.clean_cfg()
					return False, "网关不在线，或你无权访问此网关，请检查后重试"
			else:
				self.services_stop()
				self.clean_cfg()
				return False, "NPS连接错误或无此用户 {0} ".format(self.userinfo.get("name"))
		else:
			return False, "用户 {0} 正在使用中……，如需重新配置，请先停止再启动".format(self.userinfo.get("name"))

	def stop_vnet(self):
		if self._vnet_is_running:
			stop_datas = {"id": self.userinfo['gate'] + '/send_command/stop/' + str(time.time()),
			              "device": self.userinfo['gate'],
			              "data": {"device": self.userinfo['gate'] + ".freeioe_Vnet_npc", "cmd": "stop",
			                       "param": {"net": "bridge"}}
			              }
			ret, gate_stop_ret = self.TRCloudapi.post_command_to_cloud(stop_datas)
			services_stop_ret = self.services_stop()
			if services_stop_ret and ret:
				self.clean_cfg()
				return True, {"stop_time": self._stop_time, "gate_stop_return": gate_stop_ret, "services_stop_return": services_stop_ret}
			else:
				self.clean_cfg()
				return False, {"stop_time": self._stop_time, "gate_stop_return": gate_stop_ret, "services_stop_return": services_stop_ret}
		else:
			return False, "当前已经是停止状态"

	def vnet_status(self):
		now_time = int(time.time())
		if self._vnet_is_running:
			ip_alive_ret = self.check_ip_alive(self.userinfo.get("gate_lan_ip"))
			return True, {"now": now_time, "service_is_running": self._service_is_running,
				    "gate_vpn_is_running": self._gate_vpn_is_running, "vnet_is_running": self._vnet_is_running,
				    "services_status": self._services_status, "ip_alive": ip_alive_ret, "userinfo": self.userinfo}
		else:
			return False, {"now": now_time,
			               "service_is_running": self._service_is_running,
			               "vnet_is_running": self._vnet_is_running,
				            "services_status": self._services_status}

	def vnet_ready(self, gate):
		if not self.TRCloudapi:
			self.TRCloudapi = CloudApiv1(self.TRAccesskey)
		gate_online = False
		app_ready = False
		app_info = {}
		gate_status_ret = self.TRCloudapi.get_gate_status(gate)
		if gate_status_ret:
			if gate_status_ret['message'] == "ONLINE":
				gate_online = True
			else:
				gate_online = False
		if gate_online:
			gate_apps_ret = self.TRCloudapi.get_gate_apps(gate)
			if gate_apps_ret:
				gate_apps = gate_apps_ret['message']
				for app in gate_apps:
					if app.get('info').get('inst') == "freeioe_Vnet_npc":
						app_info = app.get('info')
						break
				for app in gate_apps:
					if app.get('info').get('inst') == "freeioe_Vnet_npc" and app.get('info').get('name') == "APP00000379" and app.get('info').get('running'):
						app_ready = True
						break
		return gate_online, {"ready": app_ready, "info": app_info}

	def vnet_action(self, gate, action):
		now_str = str(time.time())
		action_data = {"install": {"id": gate + '/freeioe_Vnet_npc/install/' + now_str, "device": gate,
		                           "data": {"inst": "freeioe_Vnet_npc", "name": "APP00000379", "version": 'latest',
			                           "conf": {}}},
		               "start": {"id": gate + '/freeioe_Vnet_npc/start/' + now_str, "device": gate,
		                           "data": {"inst": "freeioe_Vnet_npc"}},
		               "stop": {"id": gate + '/freeioe_Vnet_npc/stop/' + now_str, "device": gate,
		                         "data": {"inst": "freeioe_Vnet_npc"}},
		               "uninstall": {"id": gate + '/freeioe_Vnet_npc/uninstall/' + now_str, "device": gate,
		                             "data": {"inst": "freeioe_Vnet_npc"}},
		               "upgrade": {"id": gate + '/freeioe_Vnet_npc/upgrade/' + now_str, "device": gate,
		                           "data": {"inst": "freeioe_Vnet_npc", "name": "APP00000379", "version": 'latest',
			                           "conf": {}}}
		               }
		if not self.TRCloudapi:
			self.TRCloudapi = CloudApiv1(self.TRAccesskey)
		ret, gate_action_ret = None, None
		if action_data.get(action):
			ret, gate_action_ret = self.TRCloudapi.post_action_to_app(action, action_data.get(action))
		return ret, gate_action_ret


	def run(self):
		check_ip_alive_ret = None
		while not self._thread_stop:
			time.sleep(1)
			if self._vnet_is_running:
				if time.time() - self._start_time > 5:
					self._start_time = time.time()
					self.gate_vpn_data()
					self.service_status()
					if not self.userinfo['client_online']:
						self.nps_tunnel_status()
					if self.userinfo["dest_ip"]:
						check_ip_alive_ret = self.check_ip_alive(self.userinfo["dest_ip"])
				try:
					aaa = "OFFLINE"
					if self._gate_online:
						aaa = "ONLINE"
					pubinfo = self.userinfo
					if pubinfo.get('vkey'):
						del pubinfo['vkey']
					status = {"now": int(self._start_time), "vnet_is_running": self._vnet_is_running,
					          "gate_online":aaa, "gate_vpn_is_running": self._gate_vpn_is_running,
					           "service_is_running": self._service_is_running,"services_status": self._services_status,
					           "ip_alive": check_ip_alive_ret, "userinfo": pubinfo
					          }
					# print("send VNET_STATUS::")
					self._mqtt_pub.vnet_status('BRIDGE', json.dumps(status))
					# self._mqtt_pub.pub('TEST', json.dumps(status))
				except Exception as ex:
					self._log.warning('err!err!err!err!')
					self._log.exception(ex)
				print(self._heartbeat_timeout - time.time())
				if self._enable_heartbeat and time.time() > self._heartbeat_timeout:
					print("heartbeat_timeout is reachable")
					notice = {"now": int(self._start_time), "notice": "heartbeat_timeout is reachable, stop vnet"}
					self._mqtt_pub.vnet_notify('BRIDGE', json.dumps(notice))
					self.stop_vnet()
			else:
				check_ip_alive_ret = None
				if (time.time() - self._stop_time) > 10:
					self._stop_time = time.time()
					self.service_status()
				try:
					status = {"now": int(self._stop_time), "vnet_is_running": self._vnet_is_running, "service_is_running": self._service_is_running, "services_status": self._services_status}
					self._mqtt_pub.vnet_status('BRIDGE', json.dumps(status))
				except Exception as ex:
					self._log.warning(ex)

		self._log.warning("Close VNET!")

	def enable_heartbeat(self, flag, timeout):
		self._enable_heartbeat = flag
		self._heartbeat_timeout = timeout + time.time()
		if self.TRCloudapi:
			alive_ret = self.keep_vnet_alive()
			if alive_ret:
				self.TRCloudapi.gate_enable_data_one_short(self.userinfo['gate'])
				for i in range(4):
					action_ret = self.TRCloudapi.get_action_result(alive_ret.get('message'))
					if action_ret:
						self._gate_online = True
						break
					time.sleep(i + 1)
			return {"enable_heartbeat": self._enable_heartbeat, "heartbeat_timeout": self._heartbeat_timeout}
		else:
			return {}

	def keep_vnet_alive(self):
		sn = self.userinfo['gate']
		rand_id = sn + '/send_output/heartbeat_timeout/' + str(time.time())
		datas = {"id": rand_id, "device": sn,
		         "data": {"device": sn + ".freeioe_Vnet_npc", "output": 'heartbeat_timeout', "value": 60,
		                  "prop": "value"}}
		return self.TRCloudapi.action_send_output(datas)

	def start(self):
		# self._download = VNETdownload(self)
		# self._download.start()
		self.service_status()
		self.services_stop()
		# print("@@@@@@@@@@@@@@@@@@@", self._appname, self.TRAccesskey)
		threading.Thread.start(self)

	def stop(self):
		# self._download.stop()
		self._thread_stop = True
		self.join()

	def clean_cfg(self):
		self._vnet_is_running = False
		self.NPSApi = None
		self.nps_host = None
		self.__auth_key = None
		self.userinfo = {"name": None, "gate": None, "cid": None, "vkey": None, "client_status": None,
		                 "client_online": None, "tunnel_alias": None, "tid": None, "tunnel_host": None,
		                 "tunnel_port": None, "tunnel_Target": "127.0.0.1:665", "tunnel_status": None,
		                 "tunnel_online": None, "gate_lan_ip": None, "gate_lan_netmask": None, "dest_ip": None,
		                 "local_vnet_ip": None, "gate_status": None, "gate_vpn_status": None, "gate_vpn_config": None}
