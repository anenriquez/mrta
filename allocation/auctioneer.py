import uuid
import time
import logging
import logging.config
from datetime import timedelta
from allocation.round import Round

SLEEP_TIME = 0.350

""" Implements a variation of the the TeSSI algorithm using the bidding_rule and stp_method
specified in the config file
"""


class Auctioneer(object):

    def __init__(self, **kwargs):

        logging.debug("Starting Auctioneer")

        self.robots = kwargs.get('robot_ids', list())
        self.api = kwargs.get('api', None)
        self.request_alternative_timeslots = kwargs.get('request_alternative_timeslots', False)

        round_time = kwargs.get('round_time', 0)
        self.round_time = timedelta(seconds=round_time)

        self.api.add_callback(self, 'BID', 'bid_cb')

        # {robot_id: stn with tasks allocated to robot_id}
        self.stns = dict()
        # {robot_id: dispatchable graph with tasks allocated to robot_id}
        self.dispatchable_graphs = dict()

        self.tasks_to_allocate = list()
        self.allocations = list()
        self.round = Round()

    def run(self):
        if self.tasks_to_allocate and not self.round.opened:
            self.announce_task()

        if self.round.opened:
            round_result = self.round.check_closure_time()
            if round_result is not None:
                allocation, tasks_to_allocate = round_result
                self.process_allocation(allocation, tasks_to_allocate)
                self.round.close()

    def process_allocation(self, allocation, tasks_to_allocate):
        # TODO: Update stn and dispatchable graph of winning robot

        self.tasks_to_allocate = tasks_to_allocate
        self.allocations.append(allocation)

        logging.debug("Allocation: %s", allocation)
        logging.debug("Tasks left to allocate: %s ", [task.id for task in tasks_to_allocate])

        self.announce_winner(allocation)
        self.round.close()

    def allocate(self, tasks):
        if isinstance(tasks, list):
            for task in tasks:
                self.tasks_to_allocate.append(task)
            logging.debug('Auctioneer received a list of tasks')
        else:
            self.tasks_to_allocate.append(tasks)
            logging.debug('Auctioneer received one task')

    def announce_task(self):

        _round = {'tasks_to_allocate': self.tasks_to_allocate,
                  'round_time': self.round_time,
                  'n_robots': len(self.robots),
                  'request_alternative_time_slots': self.request_alternative_timeslots}

        self.round = Round(**_round)

        logging.info("Starting round: %s", self.round.id)
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
        task_announcement['payload']['round_id'] = self.round.id
        task_announcement['payload']['tasks'] = dict()

        for task in self.tasks_to_allocate:
            task_announcement['payload']['tasks'][task.id] = task.to_dict()

        logging.debug("Auctioneer announces tasks %s", [task.id for task in self.tasks_to_allocate])

        self.round.start()
        self.api.shout(task_announcement, 'TASK-ALLOCATION')

    def bid_cb(self, msg):
        bid = msg['payload']['bid']
        self.round.process_bid(bid)

    def announce_winner(self, allocation):

        allocated_task, winning_robot = allocation

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

    def shutdown(self):
        self.api.shutdown()
