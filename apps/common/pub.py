import threading
import logging
import os
import json
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
