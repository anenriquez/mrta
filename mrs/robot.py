import argparse
import logging
import time
from mrs.utils.datasets import load_yaml
from fleet_management.api import API
from fleet_management.config.config import FMSBuilder
from mrs.config.builder import RobotBuilder
from fleet_management.db.mongo import Store

_component_modules = {'api': API,
                      'robot_store': Store,
                      }

_config_order = ['api', 'robot_store']


def get_robot_config(robot_id, config_params):
    robot_config = config_params.get('robot')

    api_config = robot_config.get('api')
    api_config['zyre']['zyre_node']['node_name'] = robot_id
    robot_config.update({'api': api_config})

    db_config = robot_config.get('robot_store')
    db_config['db_name'] = db_config['db_name'] + '_' + robot_id.split('_')[1]
    robot_config.update({'robot_store': db_config})

    return robot_config


class Robot(object):
    def __init__(self, robot_id, config_file=None):
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)
        config_params = load_yaml(config_file)
        robot_config = get_robot_config(robot_id, config_params)

        logger_config = config_params.get('logger')
        logging.config.dictConfig(logger_config)

        fms_builder = FMSBuilder(component_modules=_component_modules,
                                 config_order=_config_order)
        fms_builder.configure(robot_config)

        self.api = fms_builder.get_component('api')
        self.robot_store = fms_builder.get_component('robot_store')

        robot_builder = RobotBuilder.configure(robot_id, self.api, self.robot_store, robot_config)
        self.bidder = robot_builder.get_component('bidder')

        self.api.register_callbacks(self)
        self.logger.info("Initialized Robot")

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

    robot = Robot(robot_id, config_file_path)
    robot.run()
