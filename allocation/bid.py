import logging
from stn.stp import STP


class Bid(object):

    def __init__(self, **kwargs):
        self.cost = kwargs.get('cost', float('inf'))
        self.stn_position = kwargs.get('stn_position', 0)
        self.robot_id = kwargs.get('robot_id', '')
        self.round_id = kwargs.get('round_id', '')
        self.task_id = kwargs.get('task_id', '')
        self.bidding_rule = kwargs.get('bidding_rule', None)

        stp = kwargs.get('stp', STP('fpc'))  # TeSSI by default
        self.stn = kwargs.get('stn', stp.get_stn())
        self.dispatchable_graph = kwargs.get('dispatchable_graph', stp.get_stn())

    def __repr__(self):
        return str(self.to_dict())

    def __lt__(self, other):
        if other is None:
            return False
        return self.cost < other.cost

    def __eq__(self, other):
        if other is None:
            return False
        return self.cost == other.cost

    def get_cost(self, robustness_metric):
        bid_cost = self.bidding_rule.compute_bid_cost(self.dispatchable_graph, robustness_metric)
        self.cost = bid_cost

    def get_soft_cost(self, task):
        navigation_start_time = self.dispatchable_graph.get_task_navigation_start_time(task.id)
        logging.debug("Navigation start time: %s", navigation_start_time)
        bid_cost = abs(navigation_start_time - task.earliest_start_time)
        logging.debug("Cost: %s", bid_cost)
        self.cost = bid_cost

    def to_dict(self):
        bid_dict = dict()
        bid_dict['cost'] = self.cost
        bid_dict['stn_position'] = self.stn_position
        bid_dict['robot_id'] = self.robot_id
        bid_dict['round_id'] = self.round_id
        bid_dict['task_id'] = self.task_id
        return bid_dict

    @classmethod
    def from_dict(cls, bid_dict):
        bid = cls()
        bid.cost = bid_dict['cost']
        bid.stn_position = bid_dict['stn_position']
        bid.robot_id = bid_dict['robot_id']
        bid.round_id = bid_dict['round_id']
        bid.task_id = bid_dict['task_id']
        return bid
