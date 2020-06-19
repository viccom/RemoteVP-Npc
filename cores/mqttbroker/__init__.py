#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import asyncio
import threading
from hbmqtt.broker import Broker
from cores.mqttbroker.conf import broker_config
from cores.log import log_set, configure_logger

@asyncio.coroutine
def broker_coro(config):
    broker = Broker(config)
    broker.logger = configure_logger('default', 'logs/service.log')
    broker.logger.setLevel(logging.INFO)
    yield from broker.start()


class MQTTBroker(threading.Thread):
    def __init__(self, config=None):
        threading.Thread.__init__(self)
        self._broker_config = config or broker_config

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(broker_coro(self._broker_config))
        loop.run_forever()


if __name__ == '__main__':
    formatter = "[%(asctime)s] :: %(levelname)s :: %(name)s :: %(message)s"
    logging.basicConfig(level=logging.INFO, format=formatter)
    asyncio.get_event_loop().run_until_complete(broker_coro(broker_config))
    asyncio.get_event_loop().run_forever()
