from mrs.db.models.actions import GoTo
from mrs.utils.as_dict import AsDictMixin


class Metrics(AsDictMixin):

    def __init__(self, temporal, risk):
        self.temporal = temporal
        self.risk = risk

    def __str__(self):
        to_print = ""
        to_print += "(temporal: {}, risk: {})".format(self.temporal, self.risk)
        return to_print

    def __lt__(self, other):
        if other is None:
            return False
        return self.risk < other.risk or (self.risk == other.risk and self.temporal < other.temporal)

    def __eq__(self, other):
        if other is None:
            return False
        return self.risk == other.risk and self.temporal == other.temporal

    @classmethod
    def from_dict(cls, dict_repr):
        return cls(**dict_repr)

    @property
    def cost(self):
        return self.risk, self.temporal


class BidBase(AsDictMixin):

    def __init__(self, task_id, robot_id, round_id):
        self.task_id = task_id
        self.robot_id = robot_id
        self.round_id = round_id

    @property
    def meta_model(self):
        return "bid-base"


class NoBid(BidBase):
    def __init__(self, task_id, robot_id, round_id):
        super().__init__(task_id, robot_id, round_id)

    def __str__(self):
        to_print = ""
        to_print += "NoBid(task: {}, robot: {}".format(self.task_id, self.robot_id)
        return to_print

    @property
    def meta_model(self):
        return "no-bid"


class Bid(BidBase):
    def __init__(self, task_id, robot_id, round_id, insertion_point, metrics, pre_task_action):
        self.insertion_point = insertion_point
        self.metrics = metrics
        self.pre_task_action = pre_task_action
        self._stn = None
        self._dispatchable_graph = None
        super().__init__(task_id, robot_id, round_id)

    def __str__(self):
        to_print = ""
        to_print += "Bid(task: {}, robot: {}, metrics: {}".format(self.task_id, self.robot_id, self.metrics)
        return to_print

    def __lt__(self, other):
        if other is None:
            return False
        return self.metrics < other.metrics

    def __eq__(self, other):
        if other is None:
            return False
        return self.metrics == other.metrics

    @property
    def stn(self):
        return self._stn

    @stn.setter
    def stn(self, stn):
        self._stn = stn

    @property
    def dispatchable_graph(self):
        return self._dispatchable_graph

    @dispatchable_graph.setter
    def dispatchable_graph(self, dispatchable_graph):
        self._dispatchable_graph = dispatchable_graph

    @property
    def meta_model(self):
        return "bid"

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        attrs.update(metrics=Metrics.from_dict(dict_repr.get("metrics")))
        attrs.update(pre_task_action=GoTo.from_payload(dict_repr.get("pre_task_action")))
        return attrs


class SoftBid(Bid):
    def __init__(self, task_id, robot_id, round_id, insertion_point, metrics, pre_task_action, alternative_start_time):
        super().__init__(task_id, robot_id, round_id, insertion_point, metrics, pre_task_action)
        self.alternative_start_time = alternative_start_time

    def __str__(self):
        to_print = ""
        to_print += "SoftBid(task: {}, robot: {}, alternative start time: {} metrics: {}".format(self.task_id,
                                                                                                 self.robot_id,
                                                                                                 self.alternative_start_time,
                                                                                                 self.metrics)
        return to_print

    @property
    def meta_model(self):
        return "soft-bid"


class BiddingRobot:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.bids = list()
        self.no_bids = list()

    def __str__(self):
        to_print = ""
        to_print += "{}, bids: {}, no_bids:{}".format(self.robot_id, self.bids, self.no_bids)
        return to_print

    def update(self, bid):
        if isinstance(bid, NoBid):
            self.no_bids.append(bid)
        else:
            self.bids.append(bid)

    def placed_bid(self, n_tasks):
        if len(self.bids) == 1 or len(self.no_bids) == n_tasks:
            return True
        return False
