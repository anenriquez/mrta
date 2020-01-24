import logging

from fmlib.utils.utils import load_file_from_module
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
