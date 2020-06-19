import threading
import logging
import re
import uuid
# from cores.llama import mqtt
from helper import _dict
from cores.mqttbroker.conf import AUTH

match_routes = re.compile(r'^@([^/]+)/(.+)$')


@staticmethod
def whitelist(f):
    f.whitelisted = True
    return f


class Forbidden(Exception):
    result = False
    error = "forbidden"
    description = (
        'You don\'t have the permission to access the requested resource. '
        'It is either read-protected or not readable by the server.'
    )


class NotFound(Exception):
    result = False
    error = "not_found"
    description = (
        'The requested URL was not found on the server.  '
        'If you entered the URL manually please check your spelling and '
        'try again.'
    )


class BaseService(threading.Thread):
    def __init__(self, mqtt_server, routes):
        self._mqtt_server = mqtt_server
        self._routes = routes
        self._auth = AUTH
        threading.Thread.__init__(self)

    def start(self):
        threading.Thread.start(self)

    def run(self):
        pass
        # Connect to MQTT broker and start dispatch loop
        # dispatch, receive = mqtt.connect(self._mqtt_server, self._routes, self._auth)
        # for action in receive():
        #     action_type = action["type"]
        #     payload = _dict(action.get("payload")) or _dict({})
        #     ag = match_routes.match(action_type)
        #     if ag:
        #         ag = ag.groups()
        #         route_key = ag[0]
        #         api_method = ag[1]
        #         if api_method == 'RESULT':
        #             # Skip Result topic
        #             continue
        #         api_method = "{0}_{1}".format(route_key, ag[1])
        #         logging.debug("Action: {0}  Payload {1}".format(action, action.get("payload")))
        #         id = payload.get("id") or uuid.uuid1()
        #         try:
        #             self.is_whitelisted(api_method)
        #             dispatch(getattr(self, api_method)(id, payload))
        #         except Exception as ex:
        #             logging.exception(ex)
        #             dispatch(self.failure(route_key, id, repr(ex)))
        #     else:
        #         try:
        #             logging.error(action)
        #         except Exception as ex:
        #             logging.exception(ex)

    def is_whitelisted(self, method):
        fn = getattr(self, method, None)
        if not fn:
            raise NotFound("Method {0} not found".format(method))
        elif not getattr(fn, "whitelisted", False):
            raise Forbidden("Method {0} not whitelisted".format(method))
        return True

    def failure(self, route_key, id, error_msg):
        assert (route_key is not None and self._routes[route_key])
        assert (id is not None)
        assert (error_msg is not None)
        return {
            "type": "@{0}/RESULT".format(route_key),
            "payload": {
                "id": str(id),
                "result": False,
                "error": error_msg
            },
        }

    def success(self, route_key, id, data):
        assert (route_key is not None and self._routes[route_key])
        assert (id is not None)
        assert (data is not None)
        return {
            "type": "@{0}/RESULT".format(route_key),
            "payload": {
                "id": str(id),
                "result": True,
                "data": data
            },
        }
