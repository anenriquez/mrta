import yaml
import logging
from allocation.api.zyre import ZyreAPI
# from allocation.auctioneer import Auctioneer
from allocation.task_sender import TaskSender

logging.getLogger(__name__)


class Config(object):
    def __init__(self, config_file, initialize=True):
        config = Config.load_file(config_file)
        self.config_params = dict()
        self.config_params.update(**config)
        # if initialize:
        #     self.api = self.configure_api()

    def configure_api(self, node_name):
        api_config = self.config_params.get('api')
        zyre_config = api_config.get('zyre')
        # api_config['zyre']['node_name'] = node_name
        zyre_config['node_name'] = node_name
        zyre_api = ZyreAPI(zyre_config)

        print("Zyre config: ", zyre_config)

        return zyre_api

    def configure_auctioneer(self):
        logging.info("Configuring task allocator...")
        allocation_config = self.config_params.get("task_allocation")
        fleet = self.config_params.get('fleet')
        api = self.configure_api('auctioneer')
        # auctioneer = Auctioneer(**allocator_config, robot_ids=fleet, api_config=self.api)

        return {'bidding_rule': allocation_config.get('bidding_rule'),
                'robot_ids': fleet,
                'api': api
               }

    def configure_task_sender(self):
        logging.info("Configuring task sender...")
        api = self.configure_api('task_sender')
        return {'api': api}
        # task_sender = TaskSender(api_config=api)
        # return task_sender

    def configure_robot_proxy(self, robot_id):
        logging.info("Configuring robot %s...", robot_id)
        allocation_config = self.config_params.get('task_allocation')
        api_config = self.config_params.get('api')
        api_config['zyre']['node_name'] = robot_id

        return {'robot_id': robot_id,
                'bidding_rule': allocation_config.get('bidding_rule'),
                'scheduling_method': allocation_config.get('scheduling_method'),
                'api_config': api_config,
                'auctioneer': 'auctioneer'
                }

    def get_config_params(self):
        return self.config_params

    @staticmethod
    def load_file(config_file):
        file_handle = open(config_file, 'r')
        data = yaml.safe_load(file_handle)
        file_handle.close()
        return data

    # def read_yaml_file(config_file_name):
    #     file_handle = open(config_file_name, 'r')
    #     data = yaml.safe_load(file_handle)
    #     file_handle.close()
    #     return data
