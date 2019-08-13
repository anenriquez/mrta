import logging
from mrs.utils.uuid import generate_uuid


class Bid(object):

    def __init__(self, bidding_rule=None, robot_id='', round_id='', task=None, timetable=None, cost=float('inf')):
        self.bidding_rule = bidding_rule
        self.robot_id = robot_id
        self.round_id = round_id
        self.task = task
        self.cost = cost
        self.timetable = timetable
        if not task:
            task_id = generate_uuid()
        else:
            task_id = task.id
        self.msg = BidMsg(cost, robot_id, task_id)

    def __repr__(self):
        return str(self.msg.to_dict())

    def __lt__(self, other):
        if other is None:
            return False
        return self.cost < other.cost

    def __eq__(self, other):
        if other is None:
            return False
        return self.cost == other.cost

    def compute_cost(self, position):
        dispatchable_graph = self.timetable.dispatchable_graph
        robustness_metric = self.timetable.robustness_metric

        if self.task.hard_constraints:
            self.cost = self.bidding_rule.compute_bid_cost(dispatchable_graph, robustness_metric)
            self.msg = BidMsg(self.cost, self.robot_id, self.task.id, position, self.round_id)

        else:  # soft constraints
            navigation_start_time = dispatchable_graph.get_task_navigation_start_time(self.task.id)
            logging.debug("Navigation start time: %s", navigation_start_time)
            self.cost = abs(navigation_start_time - self.task.earliest_start_time)
            alternative_start_time = navigation_start_time
            self.msg = BidMsg(self.cost, self.robot_id, self.task.id, position, self.round_id,
                                  hard_constraints=False, alternative_start_time=alternative_start_time)

        logging.debug("Cost: %s", self.cost)


class BidMsg(object):
    def __init__(self, cost=float('inf'), robot_id='', task_id='', position=0,
                 round_id='', **kwargs):
        self.cost = cost
        self.robot_id = robot_id
        self.task_id = task_id
        self.position = position
        self.round_id = round_id

        self.hard_constraints = kwargs.get('hard_constraints', True)
        self.alternative_start_time = kwargs.get('alternative_start_time')

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

    def to_dict(self):
        bid_msg_dict = dict()
        bid_msg_dict['cost'] = self.cost
        bid_msg_dict['robot_id'] = self.robot_id
        bid_msg_dict['task_id'] = self.task_id
        bid_msg_dict['position'] = self.position
        bid_msg_dict['round_id'] = self.round_id
        bid_msg_dict['hard_constraints'] = self.hard_constraints
        bid_msg_dict['alternative_start_time'] = self.alternative_start_time
        return bid_msg_dict

    @classmethod
    def from_dict(cls, bid_msg_dict):
        bid_msg = cls()
        bid_msg.cost = bid_msg_dict['cost']
        bid_msg.robot_id = bid_msg_dict['robot_id']
        bid_msg.task_id = bid_msg_dict['task_id']
        bid_msg.position = bid_msg_dict['position']
        bid_msg.round_id = bid_msg_dict['round_id']
        bid_msg.hard_constraints = bid_msg_dict['hard_constraints']
        bid_msg.alternative_start_time = bid_msg_dict['alternative_start_time']
        return bid_msg





