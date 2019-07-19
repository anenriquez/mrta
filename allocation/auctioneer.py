import uuid
import time
import logging
import logging.config
from datetime import timedelta
from allocation.round import Round
from allocation.timetable import Timetable
from stn.stp import STP


""" Implements a variation of the the TeSSI algorithm using the bidding_rule and stp_method
specified in the config file
"""


class Auctioneer(object):

    def __init__(self, **kwargs):

        logging.debug("Starting Auctioneer")

        self.robot_ids = kwargs.get('robot_ids', list())

        stp_method = kwargs.get('stp_method', None)
        stp = STP(stp_method)

        # TODO: Read timetable from db
        self.timetable = Timetable(self.robot_ids, stp)

        self.request_alternative_timeslots = kwargs.get('request_alternative_timeslots', False)
        round_time = kwargs.get('round_time', 0)
        self.round_time = timedelta(seconds=round_time)

        self.tasks_to_allocate = dict()
        self.allocations = list()
        self.round = Round()

        # TODO: Add callbacks in loader file
        self.api = kwargs.get('api', None)
        self.api.add_callback(self, 'BID', 'bid_cb')
        self.api.add_callback(self, 'FINISH-ROUND', 'finish_round_cb')

    def run(self):
        if self.tasks_to_allocate and self.round.finished:
            self.announce_task()

        if self.round.opened:
            round_result = self.round.check_closure_time()
            if round_result is not None:
                allocation = self.process_allocation(round_result)
                allocated_task, winner_robot_ids = allocation
                for robot_id in winner_robot_ids:
                    self.announce_winner(allocated_task, robot_id)

    def process_allocation(self, round_result):

        task, robot_id, position, tasks_to_allocate = round_result

        allocation = (task.id, [robot_id])
        self.allocations.append(allocation)
        self.tasks_to_allocate = tasks_to_allocate

        logging.debug("Allocation: %s", allocation)
        logging.debug("Tasks to allocate %s", self.tasks_to_allocate)

        stn = self.timetable.update_stn(robot_id, task, position)
        dispatchable_graph = self.timetable.update_dispatchable_graph(robot_id, stn)

        logging.debug("STN robot %s: %s", robot_id, stn)
        logging.debug("Dispatchable graph robot %s: %s", robot_id, dispatchable_graph)

        return allocation

    def allocate(self, tasks):
        if isinstance(tasks, list):
            for task in tasks:
                self.tasks_to_allocate[task.id] = task
            logging.debug('Auctioneer received a list of tasks')
        else:
            self.tasks_to_allocate[tasks.id] = tasks
            logging.debug('Auctioneer received one task')

    def announce_task(self):

        _round = {'tasks_to_allocate': self.tasks_to_allocate,
                  'round_time': self.round_time,
                  'n_robots': len(self.robot_ids),
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

        for task_id, task in self.tasks_to_allocate.items():
            task_announcement['payload']['tasks'][task.id] = task.to_dict()

        logging.debug("Auctioneer announces tasks %s", [task_id for task_id, task in self.tasks_to_allocate.items()])

        self.round.start()
        self.api.shout(task_announcement, 'TASK-ALLOCATION')

    def bid_cb(self, msg):
        bid = msg['payload']['bid']
        self.round.process_bid(bid)

    def finish_round_cb(self, msg):
        self.round.finish()

    def announce_winner(self, task_id, robot_id):

        allocation = dict()
        allocation['header'] = dict()
        allocation['payload'] = dict()
        allocation['header']['type'] = 'ALLOCATION'
        allocation['header']['metamodel'] = 'ropod-msg-schema.json'
        allocation['header']['msgId'] = str(uuid.uuid4())
        allocation['header']['timestamp'] = int(round(time.time()) * 1000)

        allocation['payload']['metamodel'] = 'ropod-allocation-schema.json'
        allocation['payload']['task_id'] = task_id
        allocation['payload']['winner_id'] = robot_id

        logging.debug("Accouncing winner...")
        self.api.shout(allocation, 'TASK-ALLOCATION')

    def shutdown(self):
        self.api.shutdown()
