import logging

from fmlib.utils.utils import load_file_from_module
from importlib_resources import open_text
import json
from fmlib.utils.utils import load_yaml


def load_yaml_file_from_module(module, file_name):
    try:
        file = load_file_from_module(module, file_name)
        data = load_yaml(file)
        return data
    except FileNotFoundError as e:
        logging.error(e)


def load_yaml_file(file_name):
    with open(file_name, 'r') as file_handle:
        config = load_yaml(file_handle)
    return config


def get_msg_fixture(msg_file):
    msg_module = 'mrs.messages'

    with open_text(msg_module, msg_file) as json_msg:
        msg = json.load(json_msg)

    return msg
