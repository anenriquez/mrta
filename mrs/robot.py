import argparse
import logging
import time

from mrs.config.builders import robot
from mrs.utils.datasets import load_yaml


class Robot(object):
    def __init__(self, robot_id, bidder, **kwargs):
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)

        self.robot_id = robot_id
        self.api = None
        self.robot_store = None
        self.bidder = bidder

        self.logger.info("Initialized Robot %s", robot_id)

    def configure(self, api):
        self.api = api
        self.api.register_callbacks(self)

    def run(self):
        try:
            self.api.start()
            while True:
                time.sleep(0.5)

        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.bidder.id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':

    config_file_path = '../config/config.yaml'
    parser = argparse.ArgumentParser()
    parser.add_argument('robot_id', type=str, help='example: ropod_001')
    args = parser.parse_args()
    robot_id = args.robot_id

    config_params = load_yaml(config_file_path)

    logger_config = config_params.get('logger')
    logging.config.dictConfig(logger_config)

    robot_components = robot.configure(robot_id, config_params)

    robot = Robot(robot_id, **robot_components)
    api = robot_components.get('api')
    robot.configure(api)

    robot.run()

