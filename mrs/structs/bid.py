import numpy as np


class Bid(object):
    def __init__(self, robot_id='', round_id='', task_id='', timetable=None, **kwargs):

        self.robot_id = robot_id
        self.round_id = round_id
        self.task_id = task_id
        self.timetable = timetable
        self.position = kwargs.get('position', 0)
        self.risk_metric = kwargs.get('risk_metric', np.inf)
        self.temporal_metric = kwargs.get('temporal_metric', np.inf)
        self.cost = (self.risk_metric, self.temporal_metric)
        self.hard_constraints = kwargs.get('hard_constraints', True)
        self.alternative_start_time = None

    def __repr__(self):
        return str(self.to_dict())

    def __lt__(self, other):
        if other is None:
            return False
        return self.risk_metric < other.risk_metric or \
               (self.risk_metric == other.risk_metric and self.temporal_metric < other.temporal_metric)

    def __eq__(self, other):
        if other is None:
            return False
        return self.risk_metric == other.risk_metric and self.temporal_metric == other.temporal_metric

    def to_dict(self):
        bid_dict = dict()
        bid_dict['risk_metric'] = self.risk_metric
        bid_dict['temporal_metric'] = self.temporal_metric
        bid_dict['cost'] = self.cost
        bid_dict['robot_id'] = self.robot_id
        bid_dict['task_id'] = self.task_id
        bid_dict['position'] = self.position
        bid_dict['round_id'] = self.round_id
        bid_dict['hard_constraints'] = self.hard_constraints
        bid_dict['alternative_start_time'] = self.alternative_start_time
        return bid_dict

    @classmethod
    def from_dict(cls, bid_dict):
        bid = cls()
        bid.risk_metric = bid_dict['risk_metric']
        bid.temporal_metric = bid_dict['temporal_metric']
        bid.cost = bid_dict['cost']
        bid.robot_id = bid_dict['robot_id']
        bid.task_id = bid_dict['task_id']
        bid.position = bid_dict['position']
        bid.round_id = bid_dict['round_id']
        bid.hard_constraints = bid_dict['hard_constraints']
        bid.alternative_start_time = bid_dict['alternative_start_time']
        return bid



