

MESSAGE_DECODE_ERROR_RESULT = "MESSAGE_DECODE_ERROR_RESULT"
MESSAGE_DECODE_ERROR = "MESSAGE_DECODE_ERROR"

#
# Action Creators
#
def message_decode_error_result(topic, payload, error):
    return {
        "type": MESSAGE_DECODE_ERROR_RESULT,
        "payload": {
            "topic": topic,
            "payload": payload,
            "error": error,
        },
    }


def message_decode_error(topic, payload, error):
    if type(payload) != str:
        payload = str(payload, "utf-8")

    error = str(error)
    return {
        "type": MESSAGE_DECODE_ERROR,
        "payload": {
            "topic": topic,
            "payload": payload,
            "error": error,
        },
    }

