import threading
import logging
import uuid
import ast
import re
import json
import paho.mqtt.client as mqtt
from queue import Queue
from cores.log import log_set, configure_logger
from cores.mqttbroker.conf import MQTT_PROT, AUTH

rule = re.compile(r'^([^/]+)/([^/]+)/([^/]+)/(.+)$')

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    userdata.on_connect(client, flags, rc)


def on_disconnect(client, userdata, rc):
    userdata.on_disconnect(client, rc)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        userdata.on_message(client, msg)
    except Exception as ex:
        logging.exception(ex)


class MQTTStreamPubBase(threading.Thread):
    def __init__(self, service_name, oobj):
        threading.Thread.__init__(self)
        self.host = "localhost"
        self.port = MQTT_PROT
        self.api = oobj
        self.user = AUTH.split(":")[0]
        self.pwd = AUTH.split(":")[1]
        self.clientid = "API_PUB." + service_name
        self.keepalive = 60
        self.service_name = service_name
        self.pub_queue = Queue()
        self._log = configure_logger('default', 'logs/service.log')
        self._close_connection = False

    def stop(self):
        self._close_connection = True
        self.mqttc.disconnect()

    def run(self):
        while not self._close_connection:
            try:
                mqttc = mqtt.Client(userdata=self, client_id=self.clientid)
                mqttc.username_pw_set(self.user, self.pwd)
                self.mqttc = mqttc

                mqttc.on_connect = on_connect
                mqttc.on_disconnect = on_disconnect
                mqttc.on_message = on_message

                self._log.info('MQTT (%s) Connect to %s:%d cid: %s user: %s pwd: %s', self.service_name, self.host, self.port, self.clientid, self.user, self.pwd)
                mqttc.connect_async(self.host, self.port, self.keepalive)
                mqttc.loop_forever(retry_first_connection=True)
                #
                # mqttc.connect(self.host, self.port, self.keepalive)
                # while not self._close_connection:
                #     mqttc.loop(0.2)
                #     while not self._close_connection and not self.pub_queue.empty():
                #         try:
                #             d = self.pub_queue.get_nowait()
                #             self.publish_direct(d[0], d[1], d[2])
                #         except Exception as ex:
                #             self._log.exception(ex)
                #     # continue
            except Exception as ex:
                self._log.exception(ex)
                mqttc.disconnect()

    def on_connect(self, client, flags, rc):
        self._log.info("app (%s) mqttc %s clientid (%s) connected return %d", self.service_name, self.host, self.clientid, rc)
        # 连接上MQTT Broker时订阅和模块相关的topic
        topic = "v1/{0}/api/#".format(self.service_name)
        self.mqttc.subscribe(topic)

    def on_disconnect(self, client, rc):
        self._log.info("app (%s) mqttc %s  clientid (%s) disconnect return %d", self.service_name, self.host, self.clientid, rc)

    def on_message(self, client, msg):
        self._log.info("app (%s) mqttc %s  clientid (%s) message recevied topic %s", self.service_name, self.host, self.clientid, msg.topic)
        # print(client._client_id)
        ag = rule.match(msg.topic)
        if ag:
            ag = ag.groups()
            api_method = ag[3]
            # 收到订阅的topic消息时进行处理，并执行api中定义的方法返回执行结果
            if api_method != 'RESULT':
                payload = msg.payload.decode('utf-8')
                api_method = "{0}_{1}".format(ag[2], ag[3])
                try:
                    apidata = ast.literal_eval(payload)
                    if type(apidata) is dict:
                        result = json.dumps(getattr(self.api, api_method)(apidata))
                        self.publish("RESULT", result)
                    else:
                        id = uuid.uuid1()
                        self.publish("RESULT", json.dumps({"id": str(id), "result": False, "error": "params error", "extra": None}))
                except Exception as ex:
                    self._log.error(str(ex))

    # def publish(self, topic, payload, qos=1):
    #     self.pub_queue.put([topic, payload, qos])
    #
    # def publish_direct(self, topic, payload, qos=1):

    def publish(self, topic, payload, qos=1):
        topic = "v1/{0}/api/{1}".format(self.service_name, topic)
        # print("send result::")
        return self.mqttc.publish(topic=topic, payload=payload, qos=qos)

    def subscribe(self, topic):
        topic = "v1/{0}/api/{1}".format(self.service_name, topic)
        return self.mqttc.subscribe(topic)
