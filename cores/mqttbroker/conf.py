
broker_config = {
    "listeners": {
        "default": {
            # "bind": "0.0.0.0:3883",
            # "max-connections": 1024,
            # "type": "tcp"
        },
        # "my-tcp-ssl-1": {
        #     "bind": "127.0.0.1:6883",
        #     "ssl": "on",
        #     "cafile": "KeyManager Test RSA CA_chain.crt",
        #     "certfile": "localhost_chain.crt",
        #     "keyfile": "localhost_key.key"
        # },
        # "my-ws-ssl-1": {
        #     "bind": "127.0.0.1:6884",
        #     "type": "ws",
        #     "ssl": "on",
        #     "cafile": "KeyManager Test RSA CA_chain.crt",
        #     "certfile": "localhost_chain.crt",
        #     "keyfile": "localhost_key.key"
        # },
        "my-tcp-1": {
            "bind": "0.0.0.0:3883",
            "max-connections": 1024,
            "type": "tcp"
        },
        "my-ws-1": {
            "bind": "0.0.0.0:3884",
            "max-connections": 1024,
            "type": "ws"
        }
    },
    "timeout-disconnect-delay": 2,
    "auth": {
        "allow-anonymous": False,
        "password-file": "cores/mqttbroker/user_password"
    },
    "plugins": [
        "auth_anonymous",
        "auth_file"
    ],
    "topic-check": {
        "enabled": True,
        "plugins": ["topic_taboo"]
    }
}

MQTT_PROT = 3883
MQTT_WS_PORT = 3884
AUTH = "viccom:Pa88word"
