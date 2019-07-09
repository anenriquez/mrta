import uuid
import time
import collections
import logging
import logging.config
from datetime import timedelta
from ropod.utils.timestamp import TimeStamp as ts
from allocation.config.loader import Config
# from allocation.utils.config_logging import config_logging

SLEEP_TIME = 0.350

'''  Implements the TeSSI algorithm with different bidding rules:

    - Rule 1: Lowest completion time (last task finish time - first task start time)
    - Rule 2: Lowest combination of completion time and travel distance_robot
    - Rule 3: Lowest makespan (finish time of the last task in the schedule)
    - Rule 4: Lowest combination of makespan and travel distance_robot
    - Rule 5: Lowest idle time of the robot with more tasks
'''


class Auctioneer(object):
    #  Bidding rules
    COMPLETION_TIME = 1
    COMPLETION_TIME_DISTANCE = 2
    MAKESPAN = 3
    MAKESPAN_DISTANCE = 4
    IDLE_TIME = 5

    def __init__(self, bidding_rule, robot_ids, api, request_alternative_timeslots=False, auction_time=5, **kwargs):

        logging.debug("Starting Auctioneer")

        self.bidding_rule = bidding_rule
        self.robots = robot_ids
        self.api = api
        self.request_alternative_timeslots = request_alternative_timeslots
        self.auction_time = timedelta(seconds=auction_time)

        self.api.add_callback(self, 'BID', 'bid_cb')
        self.api.add_callback(self, 'NO-BID', 'no_bid_cb')
        self.api.add_callback(self, 'ALLOCATION-INFO', 'allocation_info_cb')

        # {robot_id: stn with tasks allocated to robot_id}
        self.stns = dict()
        # {robot_id: dispatchable graph with tasks allocated to robot_id}
        self.dispatchable_graphs = dict()

        # Tasks that could not be allocated in their desired time window
        self.unsuccessful_allocations = list()
        self.tasks_to_allocate = list()
        self.auction_opened = False
        self.auction_closure_time = -1
        self.auction_time = timedelta(seconds=auction_time)
        self.allocate_next_task = True
        self.allocation_completed = False

        self.received_bids = list()
        self.received_no_bids = dict()
        self.n_round = 0
        self.allocations = dict()
        self.allocated_task = ''

    def run(self):
        if self.tasks_to_allocate and self.allocate_next_task:
            self.announce_task()

        if self.auction_opened:
            self.check_auction_closure_time()

    def allocate(self, tasks):
        if isinstance(tasks, list):
            for task in tasks:
                self.tasks_to_allocate.append(task)
            logging.debug('Auctioneer received a list of tasks')
        else:
            self.tasks_to_allocate.append(tasks)
            logging.debug('Auctioneer received one task')

    def announce_task(self):
        logging.info("Starting round: %s", self.n_round)
        logging.info("Number of tasks to allocate: %s", len(self.tasks_to_allocate))

        # Create task announcement message that contains all unallocated tasks
        task_announcement = dict()
        task_announcement['header'] = dict()
        task_announcement['payload'] = dict()
        task_announcement['header']['type'] = 'TASK-ANNOUNCEMENT'
        task_announcement['header']['metamodel'] = 'ropod-msg-schema.json'
        task_announcement['header']['msgId'] = str(uuid.uuid4())
        task_announcement['header']['timestamp'] = int(round(time.time()) * 1000)
        task_announcement['payload']['metamodel'] = 'ropod-task-announcement-schema.json'
        task_announcement['payload']['round'] = self.n_round
        task_announcement['payload']['tasks'] = dict()

        for task in self.tasks_to_allocate:
            task_announcement['payload']['tasks'][task.id] = task.to_dict()

        logging.debug("Auctioneer announces tasks %s", [task.id for task in self.tasks_to_allocate])

        self.start_auction_round()
        self.api.shout(task_announcement, 'TASK-ALLOCATION')

    def start_auction_round(self):
        self.reinitialize_auction_variables()
        self.allocate_next_task = False
        auction_open_time = ts.get_time_stamp()
        self.auction_closure_time = ts.get_time_stamp(self.auction_time)
        logging.debug("Auction round opened at %s and will close at %s", auction_open_time, self.auction_closure_time)
        self.auction_opened = True

    def reinitialize_auction_variables(self):
        self.allocated_task = ''
        self.received_bids = list()
        self.received_no_bids = dict()
        self.n_round += 1

    def check_auction_closure_time(self):
        current_time = ts.get_time_stamp()
        if current_time >= self.auction_closure_time:
            logging.debug("Closing auction round at %s", current_time)
            self.auction_opened = False
            if self.request_alternative_timeslots:
                self.check_unsucessful_allocations()
            self.elect_winner()

    def bid_cb(self, msg):
        bid = dict()
        bid['task_id'] = msg['payload']['task_id']
        bid['robot_id'] = msg['payload']['robot_id']
        bid['bid'] = msg['payload']['bid']
        self.received_bids.append(bid)
        logging.debug("Received bid %s from %s", bid['bid'], bid['robot_id'])

    def no_bid_cb(self, msg):
        task_ids = msg['payload']['task_ids']
        robot_id = msg['payload']['robot_id']
        logging.debug("Received no-bid_round from %s for tasks %s", robot_id, [task_id for task_id in task_ids])

        for task_id in task_ids:
            if task_id in self.received_no_bids:
                self.received_no_bids[task_id] += 1
            else:
                self.received_no_bids[task_id] = 1

    """ If the number of no-bids for a task is equal to the number of robots, add the task
    to the list of unallocated tasks"""
    def check_unsucessful_allocations(self):
        for task_id, n_no_bids in self.received_no_bids.items():
            if n_no_bids == len(self.robots):
                for i, task in enumerate(self.tasks_to_allocate):
                    if task.id == task_id:
                        self.tasks_to_allocate[i].hard_constraints = False
                        logging.debug("Setting soft constraints for task %s", task_id)
                        logging.debug("Adding task %s to unsuccessful_allocations", task_id)
                        self.unsuccessful_allocations.append(task)

    def allocation_info_cb(self, msg):
        robot_id = msg['payload']['robot_id']
        stn = msg['payload']['stn']
        dispatchable_graph = msg['payload']['dispatchable_graph']
        self.stns[robot_id] = stn
        self.dispatchable_graphs[robot_id] = dispatchable_graph
        logging.debug("Received allocation info of robot %s", robot_id)
        self.allocation_completed = True

    def elect_winner(self):
        if self.received_bids:
            logging.debug("Number of bids received: %s", len(self.received_bids))
            lowest_bid = float('Inf')
            ordered_bids = dict()
            robots_tied = list()

            for bid in self.received_bids:
                if bid['task_id'] not in ordered_bids:
                    ordered_bids[bid['task_id']] = dict()
                    ordered_bids[bid['task_id']]['robot_id'] = list()
                    ordered_bids[bid['task_id']]['bids'] = list()

                ordered_bids[bid['task_id']]['bids'].append(bid['bid'])
                ordered_bids[bid['task_id']]['robot_id'].append(bid['robot_id'])

            # Order dictionary by task_id
            ordered_bids = collections.OrderedDict(sorted(ordered_bids.items()))

            # Resolve ties. If more than one task has the same bid_round,
            # select the task with the lowest_id.
            # If for that task, more than a robot has a bid_round, select the robot with the lowest id

            for task_id, values in ordered_bids.items():
                if min(values['bids']) < lowest_bid:
                    lowest_bid = min(values['bids'])
                    allocated_task = task_id
                    robots_tied = list()
                    for i, robot in enumerate(values['robot_id']):
                        if values['bids'][i] == lowest_bid:
                            robots_tied.append(values['robot_id'][i])

            if len(robots_tied) > 1:
                logging.debug("For task %s there is a tie between: %s", allocated_task, [robot_id for robot_id in robots_tied])
                robots_tied.sort(key=lambda x: int(x.split('_')[-1]))

            winning_robot = robots_tied[0]

            logging.info("Robot %s wins task %s", winning_robot, allocated_task)

            self.allocations[allocated_task] = [winning_robot]
            self.allocated_task = allocated_task

            # Remove allocated task from self.tasks_to_allocate
            for i, task in enumerate(self.tasks_to_allocate):
                if task.id == allocated_task:
                    del self.tasks_to_allocate[i]

            self.announce_winner(allocated_task, winning_robot)

        else:
            logging.info("No bids received")
            self.allocation_completed = True

    def announce_winner(self, allocated_task, winning_robot):
        allocation = dict()
        allocation['header'] = dict()
        allocation['payload'] = dict()
        allocation['header']['type'] = 'ALLOCATION'
        allocation['header']['metamodel'] = 'ropod-msg-schema.json'
        allocation['header']['msgId'] = str(uuid.uuid4())
        allocation['header']['timestamp'] = int(round(time.time()) * 1000)

        allocation['payload']['metamodel'] = 'ropod-allocation-schema.json'
        allocation['payload']['task_id'] = allocated_task
        allocation['payload']['winner_id'] = winning_robot

        logging.debug("Accouncing winner...")
        self.api.shout(allocation, 'TASK-ALLOCATION')

    def get_allocation(self, task_id):
        allocation = dict()
        if task_id in self.allocations:
            robot_ids = self.allocations.pop(task_id)
            allocation[task_id] = robot_ids
            logging.debug("Allocation %s", allocation)
        else:
            logging.debug("Task %s has not been allocated", task_id)

        return allocation

    def shutdown(self):
        self.api.shutdown()
