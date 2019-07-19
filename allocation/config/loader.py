import yaml
import logging
from allocation.api.zyre import ZyreAPI
from allocation.bid import *

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
        stp_method = allocation_config.get('stp_method')
        api = self.configure_api('auctioneer')
        request_alternative_timeslots = allocation_config.get('request_alternative_timeslots')
        round_time = allocation_config.get('round_time')

        return {'robot_ids': fleet,
                'stp_method': stp_method,
                'api': api,
                'request_alternative_timeslots': request_alternative_timeslots,
                'round_time': round_time
               }

    def configure_allocation_requester(self):
        logging.info("Configuring allocation requester...")
        api = self.configure_api('allocation_requester')
        return {'api': api}

    @staticmethod
    def configure_bidding_rule():
        bidding_rule_factory = BiddingRuleFactory()
        bidding_rule_factory.register_bidding_rule('completion_time', rule_completion_time)
        bidding_rule_factory.register_bidding_rule('makespan', rule_makespan)
        return bidding_rule_factory

    @staticmethod
    def configure_compute_cost_metod():
        compute_cost_factory = ComputeCostFactory()
        compute_cost_factory.register_compute_cost_method('fpc', compute_cost_fpc)
        compute_cost_factory.register_compute_cost_method('srea', compute_cost_srea)
        compute_cost_factory.register_compute_cost_method('dsc_lp', compute_cost_dsc_lp)
        return compute_cost_factory

    def configure_robot_proxy(self, robot_id):
        logging.info("Configuring robot %s...", robot_id)
        allocation_config = self.config_params.get('task_allocation')
        bidding_rule_factory = self.configure_bidding_rule()
        compute_cost_factory = self.configure_compute_cost_metod()

        bidding_rule_name = allocation_config.get('bidding_rule')
        stp_method = allocation_config.get('stp_method')

        bidding_rule_method = bidding_rule_factory.get_bidding_rule(bidding_rule_name)
        compute_cost_method = compute_cost_factory.get_compute_cost_method(stp_method)

        api_config = self.config_params.get('api')
        api_config['zyre']['node_name'] = robot_id

        return {'robot_id': robot_id,
                'bidding_rule_method': bidding_rule_method,
                'compute_cost_method': compute_cost_method,
                'stp_method': allocation_config.get('stp_method'),
                'api_config': api_config,
                'auctioneer': 'auctioneer'
                }

    @staticmethod
    def load_file(config_file):
        file_handle = open(config_file, 'r')
        data = yaml.safe_load(file_handle)
        file_handle.close()
        return data
