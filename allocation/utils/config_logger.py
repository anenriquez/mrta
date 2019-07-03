import logging.config
import yaml


def config_logger(logging_file):

    with open(logging_file) as f:
        log_config = yaml.safe_load(f)
        logging.config.dictConfig(log_config)
