from mrs.structs.task import Task


class Bid(object):
    def __init__(self, bidding_rule=None, robot_id='', round_id='', task=Task(), timetable=None,
                 **kwargs):
        self.bidding_rule = bidding_rule
        self.robot_id = robot_id
        self.round_id = round_id
        self.task = task
        self.timetable = timetable
        self.cost = kwargs.get('cost', float('inf'))
        self.position = kwargs.get('position', 0)
        self.hard_constraints = kwargs.get('hard_constraints', True)
        self.alternative_start_time = None

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

    def compute_cost(self, position):
        dispatchable_graph = self.timetable.dispatchable_graph
        robustness_metric = self.timetable.robustness_metric
        self.position = position

        if self.task.hard_constraints:
            self.cost = self.bidding_rule.compute_bid_cost(dispatchable_graph, robustness_metric)

        else:  # soft constraints
            navigation_start_time = dispatchable_graph.get_task_navigation_start_time(self.task.id)
            self.cost = abs(navigation_start_time - self.task.earliest_start_time)
            alternative_start_time = navigation_start_time
            self.hard_constraints = False
            self.alternative_start_time = alternative_start_time

    def to_dict(self):
        bid_dict = dict()
        bid_dict['cost'] = self.cost
        bid_dict['robot_id'] = self.robot_id
        bid_dict['task_id'] = self.task.id
        bid_dict['position'] = self.position
        bid_dict['round_id'] = self.round_id
        bid_dict['hard_constraints'] = self.hard_constraints
        bid_dict['alternative_start_time'] = self.alternative_start_time
        return bid_dict

    @classmethod
    def from_dict(cls, bid_dict):
        bid = cls()
        bid.cost = bid_dict['cost']
        bid.robot_id = bid_dict['robot_id']
        bid.task_id = bid_dict['task_id']
        bid.position = bid_dict['position']
        bid.round_id = bid_dict['round_id']
        bid.hard_constraints = bid_dict['hard_constraints']
        bid.alternative_start_time = bid_dict['alternative_start_time']
        return bid



