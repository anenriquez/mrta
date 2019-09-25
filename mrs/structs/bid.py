import numpy as np
from ropod.utils.uuid import from_str


class Bid(object):
    def __init__(self, robot_id, round_id, task_id, timetable=None, **kwargs):

        self.robot_id = robot_id
        self.round_id = round_id
        self.task_id = task_id
        self.timetable = timetable
        self.position = kwargs.get('position')
        self.risk_metric = kwargs.get('risk_metric', np.inf)
        self.temporal_metric = kwargs.get('temporal_metric', np.inf)
        self.hard_constraints = kwargs.get('hard_constraints', True)
        self.alternative_start_time = kwargs.get('alternative_start_time')

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

    @property
    def cost(self):
        return self.risk_metric, self.temporal_metric

    def to_dict(self):
        bid_dict = dict()
        bid_dict['robot_id'] = self.robot_id
        bid_dict['round_id'] = self.round_id
        bid_dict['task_id'] = self.task_id
        bid_dict['position'] = self.position
        bid_dict['risk_metric'] = self.risk_metric
        bid_dict['temporal_metric'] = self.temporal_metric
        bid_dict['hard_constraints'] = self.hard_constraints
        bid_dict['alternative_start_time'] = self.alternative_start_time
        return bid_dict

    @classmethod
    def from_dict(cls, bid_dict):
        robot_id = bid_dict['robot_id']
        round_id = from_str(bid_dict['round_id'])
        task_id = from_str(bid_dict['task_id'])
        position = bid_dict['position']
        risk_metric = bid_dict['risk_metric']
        temporal_metric = bid_dict['temporal_metric']
        hard_constraints = bid_dict['hard_constraints']
        alternative_start_time = bid_dict['alternative_start_time']

        bid = cls(robot_id, round_id, task_id,
                  position=position,
                  risk_metric=risk_metric,
                  temporal_metric=temporal_metric,
                  hard_constraints=hard_constraints,
                  alternative_start_time=alternative_start_time)
        return bid

    @property
    def meta_model(self):
        return "bid"
