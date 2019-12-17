from ropod.utils.uuid import from_str

from mrs.db.models.task import InterTimepointConstraint


class Bid(object):
    def __init__(self, robot_id, round_id, task_id, **kwargs):

        self.robot_id = robot_id
        self.round_id = round_id
        self.task_id = task_id
        self.insertion_point = kwargs.get('insertion_point')
        self.travel_time = kwargs.get('travel_time')
        self.risk_metric = kwargs.get('risk_metric')
        self.temporal_metric = kwargs.get('temporal_metric')
        self.alternative_start_time = kwargs.get('alternative_start_time')

        self.stn = None
        self.dispatchable_graph = None

    def __str__(self):
        to_print = ""
        to_print += "Task: {}, Risk metric: {}, Temporal metric: {}".format(self.task_id, self.risk_metric, self.temporal_metric)
        return to_print

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
        bid_dict['insertion_point'] = self.insertion_point
        if self.travel_time:
            bid_dict['travel_time'] = self.travel_time.to_dict()
        else:
            bid_dict['travel_time'] = self.travel_time
        bid_dict['risk_metric'] = self.risk_metric
        bid_dict['temporal_metric'] = self.temporal_metric
        bid_dict['alternative_start_time'] = self.alternative_start_time
        return bid_dict

    @classmethod
    def from_payload(cls, bid_dict):
        robot_id = bid_dict['robotId']
        round_id = from_str(bid_dict['roundId'])
        task_id = from_str(bid_dict['taskId'])
        insertion_point = bid_dict['insertionPoint']
        if bid_dict.get("travelTime"):
            travel_time = InterTimepointConstraint.from_payload(bid_dict['travelTime'])
        else:
            travel_time = None
        risk_metric = bid_dict['riskMetric']
        temporal_metric = bid_dict['temporalMetric']
        alternative_start_time = bid_dict['alternativeStartTime']

        bid = cls(robot_id, round_id, task_id,
                  insertion_point=insertion_point,
                  travel_time=travel_time,
                  risk_metric=risk_metric,
                  temporal_metric=temporal_metric,
                  alternative_start_time=alternative_start_time)
        return bid

    @property
    def meta_model(self):
        return "bid"
