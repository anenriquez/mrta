import argparse
import time
import logging

""" Includes:
    - bidder
    - dispatcher
    - monitor
"""


class RobotProxy(object):

    def __init__(self, bidder):
        self.bidder = bidder

    def run(self):
        try:
            self.bidder.api.start()
            while True:
                self.bidder.api.run()
                time.sleep(0.5)

        except (KeyboardInterrupt, SystemExit):
            logging.info("Terminating %s proxy ...", robot_id)
            self.bidder.api.shutdown()
            logging.info("Exiting...")


if __name__ == '__main__':

    from fleet_management.config.loader import Config

    config_file_path = '../config/config.yaml'
    config = Config(config_file_path, initialize=False)
    config.configure_logger()
    ccu_store = config.configure_ccu_store()

    parser = argparse.ArgumentParser()
    parser.add_argument('robot_id', type=str, help='example: ropod_001')
    args = parser.parse_args()
    robot_id = args.robot_id

    robot_proxy = config.configure_robot_proxy(robot_id, ccu_store)

    robot_proxy.run()


