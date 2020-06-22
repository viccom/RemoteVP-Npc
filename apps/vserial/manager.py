import threading
import logging
import time
import json
import requests
import hashlib
import base64
from cores.log import configure_logger
from apps.vserial.tcp_client_h import TcpClientHander
from serial.tools.list_ports import comports
from apps.vserial.vs_port import VSPort
from helper import APPCtrl
from conf import nps_allowed_ports
from helper.npsManager import npsCryp, npsApiv1
from helper.thingscloud import CloudApiv1

sn_model_map = {"TRTX01": "C202", "2-30002": "Q102", "2-30100": "Q204", "2-30102": "Q204"}
model_port_map = {
    "Q102": {"com1": "/dev/ttymxc1", "com2": "/dev/ttymxc2"},
    "Q204": {"com1": "/dev/ttymxc1", "com2": "/dev/ttymxc2", "com3": "/dev/ttymxc3", "com4": "/dev/ttymxc4"},
    "C202": {"com1": "/dev/ttyS1", "com2": "/dev/ttyS2"}
}


class VSPAXManager(threading.Thread):
    def __init__(self, appname, stream_pub):
        threading.Thread.__init__(self)
        self._appname = appname
        self._ports = []
        self._thread_stop = False
        self._mqtt_stream_pub = stream_pub
        self._enable_heartbeat = APPCtrl().get_heartbeat()
        self.TRAccesskey = None
        self.TRCloudapi = None
        self.nps_host = None
        self.NPSApi = None
        self.userinfo = {"name": None, "gate": None, "cid": None, "vkey": None, "client_status": None,
                         "client_online": None, "tunnel_alias": None, "tid": None, "tunnel_host": None,
                         "tunnel_port": None, "tunnel_Target": "127.0.0.1:4678", "tunnel_status": None,
                         "tunnel_online": None, "gate_com_params": None, "gate_status": None, "gate_npc_status": None,
                         "gate_port_name": None, "local_port_name": None, "info": None}
        self.__auth_key = None
        self._gate_online = False
        self._gate_npc_is_running = False
        self._vserial_is_running = False
        self._start_time = None
        self._stop_time = None
        self._heartbeat_timeout = time.time() + 90
        self._vsport_ctrl = None
        self._log = configure_logger('default', 'logs/service.log')

    def list(self):
        return [handler.as_dict() for handler in self._ports]

    def list_ports(self):
        return [handler.get_port_key() for handler in self._ports]

    def list_all(self):
        phy_com = [c[0] for c in comports()]
        vir_com = self._vsport_ctrl.ListVir()
        for v in vir_com:
            if v not in phy_com:
                phy_com.append(v)
            pass
        return phy_com

    def list_vir(self):
        return self._vsport_ctrl.ListVir()

    def reset_bus(self):
        return self._vsport_ctrl.ResetBus()

    def get(self, name):
        for handler in self._ports:
            if handler.is_port(name):
                return handler
        return None

    def add(self, port):
        port.set_stream_pub(self._mqtt_stream_pub)
        port.start()
        self._ports.append(port)

        return True

    def remove(self, name):
        port = self.get(name)
        if not port:
            logging.error("Failed to find port {0}!!".format(name))
            return False
        port.stop()
        self._ports.remove(port)
        return True

    def info(self, name):
        handler = self.get(name)
        if not handler:
            logging.error("Failed to find port {0}!!".format(name))
            return False
        return handler.as_dict()


    def gate_vserial_data(self):
        data = self.TRCloudapi.get_device_data(self.userinfo['gate'], self.userinfo['gate'] + ".freeioe_Vserial_npc")
        if data:
            try:
                rawdata = data['message']
                # print(json.dumps(rawdata, sort_keys=False, indent=4, separators=(',', ':')))
                if rawdata:
                    if rawdata.get("npc_status").get("PV") == "running":
                        self.userinfo["gate_npc_status"] = True
                        self._gate_npc_is_running = True
                    else:
                        self.userinfo["gate_npc_status"] = False
                        self._gate_npc_is_running = False
                    if rawdata.get("current_com_params").get("PV") != "":
                        self.userinfo["gate_com_params"] = json.loads(rawdata.get("current_com_params").get("PV"))
            except Exception as ex:
                self._log.exception(ex)

    def nps_authcode(self):
        if not self.NPSApi:
            self.NPSApi = npsApiv1(self.nps_host)
        naes = npsCryp()
        retkey = self.NPSApi.nps_api_get("/auth/getauthkey")
        if retkey:
            self.__auth_key = naes.decrypt(retkey.get(
                "crypt_auth_key"))
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
                                                  {"auth_key": auth_key_md5, "timestamp": now_time,
                                                   "id": self.userinfo['tid']})
                if tunnel:
                    if tunnel.get("data"):
                        self.userinfo['client_online'] = tunnel.get("data").get("Client").get("IsConnect")

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
                                               {"auth_key": auth_key_md5, "timestamp": now_time, "start": 0,
                                                "limit": 100}).get("rows")
            if clients:
                for c in clients:
                    if c.get("Remark") == self.userinfo['name']:
                        # print("@@@@@@@@@", c.get("Remark"), self.userinfo['name'])
                        self.userinfo['cid'] = c.get("Id")
                        self.userinfo['vkey'] = c.get("VerifyKey")
                        break
                if self.userinfo['cid']:
                    tunnels = self.NPSApi.nps_api_post("/index/gettunnel/",
                                                       {"auth_key": auth_key_md5, "timestamp": now_time,
                                                        "client_id": None, "type": "tcp", "start": 0,
                                                        "limit": 100}).get("rows")
                    if tunnels:
                        for t in tunnels:
                            if not t.get("Port") in used_ports:
                                used_ports.append(t.get("Port"))
                            if t.get("Target").get("TargetStr") == self.userinfo['tunnel_Target'] and t.get(
                                    "Client").get("Remark") == self.userinfo['name']:
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
                                     "type": "tcp", "remark": self.userinfo['name'] + "_vserial_npc_proxy",
                                     "port": newPort, "target": "127.0.0.1:4678"}
                        self._log.info("{0} 增加新隧道 {1}".format(self.userinfo.get("name"), newPort))
                        ret = self.NPSApi.nps_api_post("/index/add/", newTunnel)
                        tunnels = self.NPSApi.nps_api_post("/index/gettunnel/",
                                                           {"auth_key": auth_key_md5, "timestamp": now_time,
                                                            "client_id": self.userinfo['cid'], "type": "tcp",
                                                            "start": 0, "limit": 100}).get("rows")
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

    def start_vserial(self):
        if not self._vserial_is_running:
            if not self.TRCloudapi:
                self.TRCloudapi = CloudApiv1(self.TRAccesskey)
            self.enable_heartbeat(True, 60)
            if not self.NPSApi:
                self.NPSApi = npsApiv1(self.nps_host)
            if not self.__auth_key:
                self.nps_authcode()
            if not self.userinfo['tid']:
                self.nps_tunnel()
            if self.userinfo['tid']:
                now_time = str(int(time.time()))
                auth_key_md5 = hashlib.md5((self.__auth_key + now_time).encode(encoding="UTF-8")).hexdigest()
                if not self.userinfo['client_status']:
                    # print("用户 {0} 当前禁用".format(self.userinfo["name"]))
                    ret = self.NPSApi.nps_api_post("/client/changestatus/",
                                                   {"auth_key": auth_key_md5, "timestamp": now_time,
                                                    "id": self.userinfo['cid'], "status": 1})
                if not self.userinfo['tunnel_status']:
                    # print("隧道 {0} 当前禁用".format(self.userinfo["tunnel_alias"]))
                    ret = self.NPSApi.nps_api_post("/index/start/",
                                                   {"auth_key": auth_key_md5, "timestamp": now_time,
                                                    "id": self.userinfo['tid']})
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
                    model = sn_model_map.get(self.userinfo.get("gate")[0:6]) or sn_model_map.get(self.userinfo.get("gate")[0:7]) or "C202"
                    gate_port = model_port_map.get(model).get(self.userinfo.get("gate_port_name")) or "/dev/ttyS1"
                    gate_vserial_command = {"port": gate_port, "nps": {"server_addr": self.userinfo['tunnel_host'] + ":7088",
                                                                      "vkey": self.userinfo['vkey']}, "user_id": self.userinfo['name']}
                    gate_datas = {"id": self.userinfo['gate'] + '/send_command/start/' + str(time.time()),
                                  "device": self.userinfo['gate'],
                                  "data": {"device": self.userinfo['gate'] + ".freeioe_Vserial_npc",
                                           "cmd": "start",
                                           "param": gate_vserial_command}}
                    ret, ret_content = self.TRCloudapi.post_command_to_cloud(gate_datas)
                    # print(json.dumps(ret, sort_keys=False, indent=4, separators=(',', ':')))
                    if ret:
                        if ret_content["gate_mes"]["result"]:
                            local_ports = self.list_all()
                            local_newPort = None
                            for x in range(0, len(local_ports) + 1):
                                local_newPort = "COM" + str(x+1)
                                if local_newPort not in local_ports:
                                    break
                            self.userinfo["local_port_name"] = local_newPort
                            self._vserial_is_running = True
                            self._start_time = time.time()
                            self.userinfo["info"] = {"user": self.userinfo.get("name"), "gate": self.userinfo.get("gate"), "gate_port": self.userinfo.get("gate_port_name"), "serial_driver": "vspax"}
                            handler = TcpClientHander(self.userinfo.get("local_port_name"), self.userinfo.get("tunnel_host"),
                                                      int(self.userinfo.get("tunnel_port")), self.userinfo.get("info"))
                            self.add(handler)
                            return self._vserial_is_running, self.userinfo
                        else:
                            self.clean_cfg()
                            return False, "下发指令到网关不正常，请检查后重试"
                    else:
                        self.clean_cfg()
                        return False, "网关Npc服务启动不正常，请检查后重试"
                else:
                    self.clean_cfg()
                    return False, "网关不在线，或你无权访问此网关，请检查后重试"
            else:
                self.clean_cfg()
                return False, "NPS连接错误或无此用户 {0} ".format(self.userinfo.get("name"))
        else:
            return False, "用户 {0} 正在使用中……，如需重新配置，请先停止再启动".format(self.userinfo.get("name"))

    def stop_vserial(self):
        ret2, ret_content = None, None
        ret1 = None
        if self._vserial_is_running:
            if self._gate_online:
                gate_datas = {"id": self.userinfo['gate'] + '/send_command/stop/' + str(time.time()),
                              "device": self.userinfo['gate'],
                              "data": {"device": self.userinfo['gate'] + ".freeioe_Vserial_npc",
                                       "cmd": "stop",
                                       "param": {}}}
                ret2, ret_content = self.TRCloudapi.post_command_to_cloud(gate_datas)
            else:
                ret2, ret_content = True, "网关离线，需手动关闭网关中的服务"
            if ret2:
                ret1 = self.remove(self.userinfo.get("local_port_name"))
            if ret1 and ret2:
                self._stop_time = time.time()
                self.clean_cfg()
                return True, "停止虚拟串口成功"
            else:
                self.clean_cfg()
                return False, "关闭失败"
        else:
            return False, "服务已停止"

    def vserial_status(self):
        now_time = int(time.time())
        if self._vserial_is_running:
            return True, {"now": now_time,
                          "gate_online": self._gate_online,
                          "gate_npc_is_running": self._gate_npc_is_running,
                          "vserial_is_running": self._vserial_is_running,
                           "userinfo": self.userinfo}
        else:
            return False, {"now": now_time, "vserial_is_running": self._vserial_is_running}

    def vserial_ready(self, gate):
        if not self.TRCloudapi:
            self.TRCloudapi = CloudApiv1(self.TRAccesskey)
        gate_online = False
        app_ready = False
        app_info ={}
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
                    if app.get('info').get('inst') == "freeioe_Vserial_npc":
                        app_info = app.get('info')
                        break
                for app in gate_apps:
                    if app.get('info').get('inst') == "freeioe_Vserial_npc" and app.get('info').get(
                            'name') == "APP00000378" and app.get('info').get('running'):
                        app_ready = True
                        break
        return gate_online, {"ready": app_ready, "info": app_info}

    def vserial_action(self, gate, action):
        now_str = str(time.time())
        action_data = {"install": {"id": gate + '/freeioe_Vserial_npc/install/' + now_str, "device": gate,
                                   "data": {"inst": "freeioe_Vserial_npc", "name": "APP00000378", "version": 'latest',
                                            "conf": {}}},
                       "start": {"id": gate + '/freeioe_Vserial_npc/start/' + now_str, "device": gate,
                                 "data": {"inst": "freeioe_Vserial_npc"}},
                       "stop": {"id": gate + '/freeioe_Vserial_npc/stop/' + now_str, "device": gate,
                                 "data": {"inst": "freeioe_Vserial_npc"}},
                       "uninstall": {"id": gate + '/freeioe_Vserial_npc/uninstall/' + now_str, "device": gate,
                                     "data": {"inst": "freeioe_Vserial_npc"}},
                       "upgrade": {"id": gate + '/freeioe_Vserial_npc/upgrade/' + now_str, "device": gate,
                                   "data": {"inst": "freeioe_Vserial_npc", "name": "APP00000378", "version": 'latest',
                                            "conf": {}}}}
        if not self.TRCloudapi:
            self.TRCloudapi = CloudApiv1(self.TRAccesskey)
        ret, gate_action_ret = None, None
        if action_data.get(action):
            ret, gate_action_ret = self.TRCloudapi.post_action_to_app(action, action_data.get(action))
        return ret, gate_action_ret

    def start(self):
        # if APPCtrl().get_accesskey():
        #     self.TRAccesskey = APPCtrl().get_accesskey()
        # print("@@@@@@@@@@@@@@@@@@@", self._appname, self.TRAccesskey)
        self._stop_time = time.time()
        threading.Thread.start(self)

    def run(self):
        self._vsport_ctrl = VSPort()
        self._vsport_ctrl.init()
        while not self._thread_stop:
            time.sleep(1)
            if self._vserial_is_running:
                if time.time() - self._start_time > 5:
                    self._start_time = time.time()
                    self.gate_vserial_data()
                    if not self.userinfo['client_online']:
                        self.nps_tunnel_status()
                for handler in self._ports:
                    try:
                        gateonline = "OFFLINE"
                        if self._gate_online:
                            gateonline = "ONLINE"
                        vinfo = handler.as_dict()
                        vinfo["now"] = str(int(self._start_time))
                        vinfo["vserial_is_running"] = self._vserial_is_running
                        vinfo["gate_online"] = gateonline
                        vinfo["client_online"] = self.userinfo["client_online"]
                        vinfo["gate_npc_status"] = self.userinfo["gate_npc_status"]
                        vinfo["gate_port_name"] = self.userinfo["gate_port_name"]
                        vinfo["gate_com_params"] = self.userinfo["gate_com_params"]
                        self._mqtt_stream_pub.vspax_status(handler.get_port_key(), json.dumps(vinfo))
                        self._mqtt_stream_pub.vspax_info(handler.get_port_key(), json.dumps(self.userinfo))
                    except Exception as ex:
                        logging.exception(ex)
                print(self._heartbeat_timeout - time.time())
                if self._enable_heartbeat and time.time() > self._heartbeat_timeout:
                    print("heartbeat_timeout is reachable")
                    notice = {"now": str(int(self._start_time)), "notice": "heartbeat_timeout is reachable, stop vnet"}
                    self._mqtt_stream_pub.vspax_notify(handler.get_port_key(), json.dumps(notice))
                    self.stop_vserial()
            else:
                status = {"now": str(int(time.time())), "vserial_is_running": self._vserial_is_running, "local_com": None}
                self._mqtt_stream_pub.vspax_status("COM0", json.dumps(status))

        self._vsport_ctrl.close()
        logging.warning("VSPAX Manager Closed!!!")


    def enable_heartbeat(self, flag, timeout):
        self._enable_heartbeat = flag
        self._heartbeat_timeout = time.time() + timeout
        alive_ret = self.keep_vspax_alive()
        if alive_ret:
            self.TRCloudapi.gate_enable_data_one_short(self.userinfo['gate'])
            for i in range(4):
                action_ret = self.TRCloudapi.get_action_result(alive_ret.get('message'))
                if action_ret:
                    self.userinfo['gate_status'] = "ONLINE"
                    break
                time.sleep(i + 1)
        return {"enable_heartbeat": self._enable_heartbeat, "heartbeat_timeout": self._heartbeat_timeout}

    def keep_vspax_alive(self):
        if self.userinfo['gate']:
            datas = {
                "id": self.userinfo['gate'] + '/send_output/heartbeat_timeout/' + str(time.time()),
                "device": self.userinfo['gate'],
                "data": {
                    "device": self.userinfo['gate'] + ".freeioe_Vserial_npc",
                    "output": 'heartbeat_timeout',
                    "value": 60,
                    "prop": "value"
                }
            }
            self.TRCloudapi.action_send_output(datas)

    def stop(self):
        self._thread_stop = True
        self.join(3)

    def clean_all(self):
        keys = [h.get_port_key() for h in self._ports]
        for name in keys:
            try:
                self.remove(name)
            except Exception as ex:
                logging.exception(ex)

    def clean_cfg(self):
        self._vserial_is_running = False
        self.NPSApi = None
        self.nps_host = None
        self.__auth_key = None
        self.userinfo = {"name": None, "gate": None, "cid": None, "vkey": None, "client_status": None,
                         "client_online": None, "tunnel_alias": None, "tid": None, "tunnel_host": None,
                         "tunnel_port": None, "tunnel_Target": "127.0.0.1:4678", "tunnel_status": None,
                         "tunnel_online": None, "gate_com_params": None, "gate_npc_status": None,
                         "gate_port_name": None, "local_port_name": None, "info": None}