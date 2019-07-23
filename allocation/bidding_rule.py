
class TemporalMetricFunctionFactory(object):
    """ Registers and retrieves functions to compute temporal metrics
    """
    def __init__(self):
        self._temporal_metric_functions = {}

    def register_temporal_metric_function(self, temporal_metric, temporal_metric_function):
        self._temporal_metric_functions[temporal_metric] = temporal_metric_function

    def get_temporal_metric_function(self, temporal_metric):
        temporal_metric_function = self._temporal_metric_functions.get(temporal_metric)
        if not temporal_metric_function:
            raise ValueError(temporal_metric)

        return temporal_metric_function


def get_completion_time(dispatchable_graph):
    return dispatchable_graph.get_completion_time()


def get_makespan(dispatchable_graph):
    return dispatchable_graph.get_makespan()


class BiddingRuleFactory(object):
    """ Registers and retrieves bidding rules
    """
    def __init__(self):
        self._bidding_rules = {}

    def register_bidding_rule(self, stp_solver, bidding_rule):
        self._bidding_rules[stp_solver] = bidding_rule

    def get_bidding_rule(self, stp_solver):
        bidding_rule = self._bidding_rules.get(stp_solver)
        if not bidding_rule:
            raise ValueError(stp_solver)

        return bidding_rule


def bidding_rule_fpc(robustness_metric, temporal_metric):
    bid_cost = temporal_metric * robustness_metric
    return bid_cost


def bidding_rule_srea(robustness_metric, temporal_metric):
    """

    :param robustness_metric: level of risk, a lower value is preferable
    :param temporal_metric:
    :return:
    """
    bid_cost = temporal_metric * robustness_metric
    return bid_cost


def bidding_rule_dsc_lp(robustness_metric, temporal_metric):
    """

    :param robustness_metric: degree of strong controllability, a larger value is preferable
    :param temporal_metric:
    :return:
    """
    bid_cost = float('inf')  # Equivalent to a no-bid

    threshold = 0.7
    if robustness_metric > threshold:
        bid_cost = temporal_metric/robustness_metric

    return bid_cost


class BiddingRule(object):
    def __init__(self, robustness_metric, temporal_metric):
        temporal_metric_function_factory = TemporalMetricFunctionFactory()
        temporal_metric_function_factory.register_temporal_metric_function('completion_time', get_completion_time)
        temporal_metric_function_factory.register_temporal_metric_function('makespan', get_makespan)

        bidding_rule_factory = BiddingRuleFactory()
        bidding_rule_factory.register_bidding_rule('fpc', bidding_rule_fpc)
        bidding_rule_factory.register_bidding_rule('srea', bidding_rule_srea)
        bidding_rule_factory.register_bidding_rule('dsc_lp', bidding_rule_dsc_lp)

        self.bidding_rule = bidding_rule_factory.get_bidding_rule(robustness_metric)
        self.temporal_metric_function = temporal_metric_function_factory.get_temporal_metric_function(temporal_metric)

    def compute_bid_cost(self, dispatchable_graph, robustness_metric):
        temporal_metric = self.temporal_metric_function(dispatchable_graph)
        bid_cost = self.bidding_rule(robustness_metric, temporal_metric)
        return bid_cost
