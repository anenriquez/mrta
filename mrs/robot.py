import argparse
import time
import logging

""" Includes:
    - bidder
    - dispatcher
    - monitor
"""


class Robot(object):

    def __init__(self, api, bidder, **kwargs):
        self.api = api
        self.bidder = bidder
        self.dispatcher = kwargs.get('dispatcher')

    def run(self):
        try:
            self.api.start()
            while True:
                self.bidder.api.run()
                if self.dispatcher is not None:
                    self.dispatcher.run()
                time.sleep(0.5)

        except (KeyboardInterrupt, SystemExit):
            logging.info("Terminating %s robot ...")
            self.api.shutdown()
            logging.info("Exiting...")


if __name__ == '__main__':

    from fleet_management.config.loader import Config, register_api_callbacks

    config_file_path = '../config/config.yaml'
    config = Config(config_file_path, initialize=False)
    config.configure_logger()
    ccu_store = config.configure_ccu_store()

    parser = argparse.ArgumentParser()
    parser.add_argument('robot_id', type=str, help='example: ropod_001')
    args = parser.parse_args()
    robot_id = args.robot_id

    robot = config.configure_robot_proxy(robot_id, ccu_store, dispatcher=True)

    register_api_callbacks(robot, robot.api)

    robot.run()


