import json
import logging
import os
import base64
from cores.mqttc.lite import MQTTStreamPubBase


class MQTTPub(MQTTStreamPubBase):
    def __init__(self, id):
        self._id = id
        MQTTStreamPubBase.__init__(self, id)

    def pub(self, key, data):
        topic = self._id.upper() + "/{0}".format(key.upper())
        if type(data) is dict:
            data = json.dumps(data)
        if not type(data) is str:
            data = str(data)
        return self.mqttc.publish(topic=topic, payload=data, qos=1)

    def vspax_out_pub(self, key, data):
        topic = self._id.upper() + "/VSPAX/{0}/OUT".format(key)
        payload = base64.b64encode(data)
        return self.mqttc.publish(topic=topic, payload=payload, qos=1)

    def vspax_in_pub(self, key, data):
        topic = self._id.upper() + "/VSPAX/{0}/IN".format(key)
        payload = base64.b64encode(data)
        return self.mqttc.publish(topic=topic, payload=payload, qos=1)

    def socket_out_pub(self, key, data):
        topic = self._id.upper() + "/SOCKET/{0}/OUT".format(key)
        payload = base64.b64encode(data)
        return self.mqttc.publish(topic=topic, payload=payload, qos=1)

    def socket_in_pub(self, key, data):
        topic = self._id.upper() + "/SOCKET/{0}/IN".format(key)
        payload = base64.b64encode(data)
        return self.mqttc.publish(topic=topic, payload=payload, qos=1)

    def vspax_status(self, key, data):
        topic = self._id.upper() + "/STATUS/{0}".format(key.upper())
        if type(data) is dict:
            data = json.dumps(data)
        if not type(data) is str:
            data = str(data)
        return self.mqttc.publish(topic=topic, payload=data, qos=1)

    def vspax_info(self, key, data):
        topic = self._id.upper() + "/INFO/{0}".format(key.upper())
        if type(data) is dict:
            data = json.dumps(data)
        if not type(data) is str:
            data = str(data)
        return self.mqttc.publish(topic=topic, payload=data, qos=1)

    def vspax_notify(self, key, action, data):
        topic = self._id.upper() + "/NOTIFY/{0}".format(key)
        if type(data) is dict:
            data = json.dumps(data)
        if not type(data) is str:
            data = str(data)
        return self.mqttc.publish(topic=topic, payload=json.dumps({"type": action, "info": data}), qos=1)