from fmlib.utils.messages import Document
from ropod.utils.uuid import from_str

from mrs.db.models.task import InterTimepointConstraint
from mrs.utils.dictionaries import AsDictMixin


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

    @property
    def cost(self):
        return self.risk, self.temporal


class BidBase(AsDictMixin):

    def __init__(self, task_id, robot_id, round_id):
        self.task_id = task_id
        self.robot_id = robot_id
        self.round_id = round_id

    @classmethod
    def to_document(cls,  payload):
        document = Document.from_payload(payload)
        document.pop("metamodel")
        document.update(task_id=from_str(document["task_id"]))
        document.update(round_id=from_str(document["round_id"]))
        return document

    @classmethod
    def from_payload(cls, payload):
        document = cls.to_document(payload)
        return cls(**document)

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
    def __init__(self, task_id, robot_id, round_id, insertion_point, metrics, travel_time):
        self.insertion_point = insertion_point
        self.metrics = metrics
        self.travel_time = travel_time
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
    def from_payload(cls, payload):
        document = cls.to_document(payload)
        document.update(travel_time=InterTimepointConstraint.from_payload(document["travel_time"]))
        document.update(metrics=Metrics.from_dict(document["metrics"]))
        return cls(**document)


class SoftBid(Bid):
    def __init__(self, task_id, robot_id, round_id, insertion_point, metrics, travel_time, alternative_start_time):
        super().__init__(task_id, robot_id, round_id, insertion_point, metrics, travel_time)
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
            print("Robot {} placed bids".format(self.robot_id))
            return True
        return False
