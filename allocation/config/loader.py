import yaml
import logging
from allocation.api.zyre import ZyreAPI
from allocation.bidding_rule import BiddingRule

logging.getLogger(__name__)


class Config(object):
    def __init__(self, config_file):
        config = Config.load_file(config_file)
        self.config_params = dict()
        self.config_params.update(**config)

    def configure_api(self, node_name):
        api_config = self.config_params.get('api')
        zyre_config = api_config.get('zyre')
        zyre_config['node_name'] = node_name
        zyre_api = ZyreAPI(zyre_config)
        return zyre_api

    def configure_auctioneer(self):
        logging.info("Configuring auctioneer...")
        allocation_config = self.config_params.get("task_allocation")
        fleet = self.config_params.get('fleet')
        bidding_rule_config = allocation_config.get('bidding_rule')
        stp_solver = bidding_rule_config.get('robustness')
        api = self.configure_api('auctioneer')
        alternative_timeslots = allocation_config.get('alternative_timeslots')
        round_time = allocation_config.get('round_time')

        return {'robot_ids': fleet,
                'stp_solver': stp_solver,
                'api': api,
                'alternative_timeslots': alternative_timeslots,
                'round_time': round_time
               }

    def configure_allocation_requester(self):
        logging.info("Configuring allocation requester...")
        api = self.configure_api('allocation_requester')
        return {'api': api}

    def configure_robot_proxy(self, robot_id):
        logging.info("Configuring robot %s...", robot_id)
        allocation_config = self.config_params.get('task_allocation')
        bidding_rule_config = allocation_config.get('bidding_rule')
        robustness = bidding_rule_config.get('robustness')
        temporal = bidding_rule_config.get('temporal')
        bidding_rule = BiddingRule(robustness, temporal)

        api_config = self.config_params.get('api')
        api_config['zyre']['node_name'] = robot_id

        return {'robot_id': robot_id,
                'bidding_rule': bidding_rule,
                'stp_solver': robustness,
                'api_config': api_config,
                'auctioneer': 'auctioneer'
                }

    @staticmethod
    def load_file(config_file):
        file_handle = open(config_file, 'r')
        data = yaml.safe_load(file_handle)
        file_handle.close()
        return data
