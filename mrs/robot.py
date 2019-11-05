import argparse
import logging.config
import time

from mrs.config.builders import robot
from fmlib.config.params import ConfigParams

ConfigParams.default_config_module = 'mrs.config.default'


def get_robot_components(robot_id, config_file=None):
    if config_file is None:
        config_params = ConfigParams.default()
    else:
        config_params = ConfigParams.from_file(config_file)

    logger_config = config_params.get('logger')
    logging.config.dictConfig(logger_config)

    components = robot.configure(robot_id, config_params)

    return components


class Robot(object):
    def __init__(self, robot_id, bidder, **kwargs):
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)

        self.robot_id = robot_id
        self.bidder = bidder

        self.api = kwargs.get('api')
        if self.api:
            self.api.register_callbacks(self)

        self.robot_store = kwargs.get('robot_store')

        self.logger.info("Initialized Robot %s", robot_id)

    def configure(self, **kwargs):
        api = kwargs.get('api')
        robot_store = kwargs.get('robot_store')
        if api:
            self.api = api
            self.api.register_callbacks(self)
        if robot_store:
            self.robot_store = robot_store

    def run(self):
        try:
            self.api.start()
            while True:
                time.sleep(0.5)

        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.bidder.robot_id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')

    parser.add_argument('robot_id', type=str, help='example: ropod_001')

    args = parser.parse_args()

    robot_components = get_robot_components(args.robot_id, args.file)

    new_robot = Robot(args.robot_id, **robot_components)
    new_robot.run()




