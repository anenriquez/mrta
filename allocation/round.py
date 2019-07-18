from allocation.utils.uuid import generate_uuid
import logging
from ropod.utils.timestamp import TimeStamp as ts
from allocation.bid import Bid
import copy


class Round(object):

    def __init__(self, **kwargs):

        self.tasks_to_allocate = kwargs.get('tasks_to_allocate', list())
        self.round_time = kwargs.get('round_time', 0)
        self.n_robots = kwargs.get('n_robots', 0)
        self.request_alternative_timeslots = kwargs.get('request_alternative_timeslots', False)

        self.closure_time = 0
        self.id = generate_uuid()
        self.opened = False
        self.received_bids = dict()
        self.received_no_bids = dict()

    def start(self):
        open_time = ts.get_time_stamp()
        self.closure_time = ts.get_time_stamp(self.round_time)
        logging.debug("Round opened at %s and will close at %s",
                          open_time, self.closure_time)
        self.opened = True

    def process_bid(self, bid_dict):
        bid = Bid.from_dict(bid_dict)

        logging.debug("Processing bid from robot %s, cost: %s",
                          bid.robot_id, bid.cost)

        if bid.cost != float('inf'):
            # Process a bid
            if bid.task_id not in self.received_bids or \
                    self.update_task_bid(bid, self.received_bids[bid.task_id]):

                self.received_bids[bid.task_id] = bid

        else:
            # Process a no-bid
            self.received_no_bids[bid.task_id] = self.received_no_bids.get(bid.task_id, 0) + 1

    @staticmethod
    def update_task_bid(new_bid, old_bid):
        """ Called when more than one bid is received for the same task

        :return: boolean
        """
        old_robot_id = int(old_bid.robot_id.split('_')[-1])
        new_robot_id = int(new_bid.robot_id.split('_')[-1])

        if new_bid < old_bid or (new_bid == old_bid and new_robot_id < old_robot_id):
            return True

        return False

    def check_closure_time(self):
        """ Calls self.close() when it is time to close the round
        """
        current_time = ts.get_time_stamp()

        if current_time < self.closure_time:
            return None

        logging.debug("Closing round at %s", current_time)

        round_result = self.get_round_results()

        if round_result is None:
            return None

        allocation, tasks_to_allocate = round_result

        logging.debug("Allocation: %s", allocation)
        logging.debug("Tasks left to allocate: %s", [task.id for task in tasks_to_allocate])

        return allocation, tasks_to_allocate

    def get_round_results(self):
        """ Closes the round and returns the allocation of the round and
        the tasks that need to be announced in the next round

        :return:
        allocation(dict): key - task_id,
                          value - list of robots assigned to the task

        tasks_to_allocate(list): tasks left to allocate

        """
        # Check for which tasks the constraints need to be set to soft
        if self.request_alternative_timeslots and self.received_no_bids:
            self.set_soft_constraints()

        # Get the allocation of this round
        allocation = self.elect_winner()
        if allocation is None:
            return None

        allocated_task, winning_robot = allocation

        # Remove allocated task from tasks_to_allocate
        for i, task in enumerate(self.tasks_to_allocate):
            if task.id == allocated_task:
                del self.tasks_to_allocate[i]

        return allocation, self.tasks_to_allocate

    def close(self):
        self.opened = False
        logging.debug("Round closed")

    def set_soft_constraints(self):
        """ If the number of no-bids for a task is equal to the number of robots,
        set the temporal constraints be soft
        """

        for task_id, n_no_bids in self.received_no_bids.items():
            if n_no_bids == self.n_robots:
                for i, task in enumerate(self.tasks_to_allocate):
                    if task.id == task_id:
                        self.tasks_to_allocate[i].hard_constraints = False
                        logging.debug("Setting soft constraints for task %s", task_id)

    def elect_winner(self):
        """ Elects the winner of the round

        :return:
        allocation(dict): key - task_id,
                          value - list of robots assigned to the task

        """
        lowest_bid = Bid()

        for task_id, bid in self.received_bids.items():
            if bid < lowest_bid:
                lowest_bid = copy.deepcopy(bid)

        if lowest_bid.cost == float('inf'):
            # TODO: ADD exception: No allocation
            return None

        allocation = (lowest_bid.task_id, lowest_bid.robot_id)

        return allocation
