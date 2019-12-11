import json

from importlib_resources import open_text


def get_msg_fixture(msg_file):
    msg_module = 'mrs.tests.fixtures.messages'

    with open_text(msg_module, msg_file) as json_msg:
        msg = json.load(json_msg)

    return msg
