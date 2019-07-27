import yaml
import logging
from allocation.api.zyre import ZyreAPI
from allocation.auctioneer import Auctioneer
from allocation.robot import Robot
logging.getLogger(__name__)


class Config(object):
    def __init__(self, config_file):
        config = Config.load_file(config_file)
        self.config_params = dict()
        self.config_params.update(**config)

    def configure_api(self, node_name):
        api_config = self.config_params.get('api')
        zyre_config = api_config.get('zyre').get('zyre_node')  # Arguments for the zyre_base class
        zyre_config['node_name'] = node_name
        api = ZyreAPI(zyre_config)

        return api

    def configure_auctioneer(self):
        logging.info("Configuring auctioneer...")
        allocation_config = self.config_params.get("task_allocation")

        api = self.configure_api('auctioneer')
        fleet = self.config_params.get('fleet')
        ccu_store = None
        stp_solver = allocation_config.get('bidding_rule').get('robustness')

        auctioneer = Auctioneer(robot_ids=fleet, ccu_store=ccu_store, api=api,
                                stp_solver=stp_solver, **allocation_config)

        return auctioneer

    def configure_allocation_requester(self):
        logging.info("Configuring allocation requester...")
        api = self.configure_api('allocation_requester')
        return {'api': api}

    def configure_robot_proxy(self, robot_id, ccu_store):
        logging.info("Configuring robot %s...", robot_id)
        allocation_config = self.config_params.get('task_allocation')

        api_config = self.config_params.get('api')
        zyre_config = api_config.get('zyre').get('zyre_node')  # Arguments for the zyre_base class
        zyre_config['node_name'] = robot_id + '_proxy'
        zyre_config['groups'] = ['TASK-ALLOCATION']
        api = ZyreAPI(zyre_config)

        bidding_rule_config = allocation_config.get('bidding_rule')

        robot = Robot(robot_id=robot_id, ccu_store=ccu_store, api=api,
                      bidding_rule_config=bidding_rule_config, **allocation_config)

        return robot

    @staticmethod
    def load_file(config_file):
        file_handle = open(config_file, 'r')
        data = yaml.safe_load(file_handle)
        file_handle.close()
        return data
