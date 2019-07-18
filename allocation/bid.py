import logging


class BiddingRuleFactory(object):
    """ Registers and retrieves bidding_rule functions based on a
    bidding_rule_name
    """
    def __init__(self):
        self._bidding_rules = {}

    def register_bidding_rule(self, bidding_rule_name, bidding_rule):
        self._bidding_rules[bidding_rule_name] = bidding_rule

    def get_bidding_rule(self, bidding_rule_name):
        bidding_rule = self._bidding_rules.get(bidding_rule_name)
        if not bidding_rule:
            raise ValueError(bidding_rule)

        return bidding_rule


def rule_completion_time(dispatchable_graph):
    return dispatchable_graph.get_completion_time()


def rule_makespan(dispatchable_graph):
    return dispatchable_graph.get_makespan()


class ComputeCostFactory(object):
    """ Registers and retrieves compute_cost functions based on the stp_method

    """
    def __init__(self):
        self._compute_cost_methods = {}

    def register_compute_cost_method(self, stp_method, compute_cost_method):
        self._compute_cost_methods[stp_method] = compute_cost_method

    def get_compute_cost_method(self, stp_method):
        compute_cost_method = self._compute_cost_methods.get(stp_method)
        if not compute_cost_method:
            raise ValueError(stp_method)

        return compute_cost_method


def compute_cost_fpc(stp_metric, bidding_rule_result):
    cost = bidding_rule_result
    return cost


def compute_cost_srea(stp_metric, bidding_rule_result):
    """

    :param stp_metric: level of risk, a lower value is preferable
    :param bidding_rule_result:
    :return:
    """
    cost = bidding_rule_result * stp_metric
    return cost


def compute_cost_dsc_lp(stp_metric, bidding_rule_result):
    """

    :param stp_metric: degree of strong controllability, a larger value is preferable
    :param bidding_rule_result:
    :return:
    """
    threshold = 0.7
    if stp_metric > threshold:
        cost = bidding_rule_result/stp_metric

    cost = float('inf')  # Equivalent to a no-bid

    return cost


class Bid(object):

    def __init__(self, **kwargs):
        self.cost = kwargs.get('cost', float('inf'))
        self.stn_position = kwargs.get('stn_position', 0)
        self.robot_id = kwargs.get('robot_id', '')
        self.round_id = kwargs.get('round_id', '')
        self.task_id = kwargs.get('task_id', '')
        self.bidding_rule = kwargs.get('bidding_rule', None)
        self.compute_cost = kwargs.get('compute_cost', None)

        self.stn = kwargs.get('stn', None)
        self.dispatchable_graph = kwargs.get('dispatchable_graph', None)

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

    def get_cost(self, stp_metric):
        bidding_rule_result = self.bidding_rule(self.dispatchable_graph)
        logging.debug("STP metric %s", stp_metric)
        logging.debug("biddin_rule_result %s", bidding_rule_result)
        cost = self.compute_cost(stp_metric, bidding_rule_result)
        logging.debug("Cost %s", cost)
        self.cost = cost

    def get_soft_cost(self, task):
        navigation_start_time = self.dispatchable_graph.get_task_navigation_start_time(task.id)
        logging.debug("Navigation start time: %s", navigation_start_time)
        cost = abs(navigation_start_time - task.earliest_start_time)
        logging.debug("Cost: %s", cost)
        self.cost = cost

    def to_dict(self):
        bid_dict = dict()
        bid_dict['cost'] = self.cost
        bid_dict['stn_position'] = self.stn_position
        bid_dict['robot_id'] = self.robot_id
        bid_dict['round_id'] = self.round_id
        bid_dict['task_id'] = self.task_id
        return bid_dict

    def get_allocation_info(self):
        return self.stn, self.dispatchable_graph

    @classmethod
    def from_dict(cls, bid_dict):
        bid = cls()
        bid.cost = bid_dict['cost']
        bid.stn_position = bid_dict['stn_position']
        bid.robot_id = bid_dict['robot_id']
        bid.round_id = bid_dict['round_id']
        bid.task_id = bid_dict['task_id']
        return bid
