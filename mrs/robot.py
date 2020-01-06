import argparse
import logging.config
import time

from mrs.config.configurator import Configurator


class Robot:
    def __init__(self, robot_id, api, robot_store, executor_interface, **kwargs):
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)

        self.robot_id = robot_id
        self.api = api
        self.robot_store = robot_store
        self.executor_interface = executor_interface

        self.api.register_callbacks(self)
        self.logger.info("Initialized Robot %s", robot_id)

    def run(self):
        try:
            self.api.start()
            while True:
                self.executor_interface.run()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.robot_id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    args = parser.parse_args()

    config = Configurator(args.file)
    components = config.config_robot(args.robot_id)

    robot = Robot(**components)
    robot.run()

