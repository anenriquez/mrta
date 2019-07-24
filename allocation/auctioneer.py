import uuid
import time
import logging
import logging.config
from datetime import timedelta
from allocation.round import Round
from allocation.timetable import Timetable
from stn.stp import STP
from allocation.exceptions.no_allocation import NoAllocation
from allocation.exceptions.alternative_timeslot import AlternativeTimeSlot


""" Implements a variation of the the TeSSI algorithm using the bidding_rule 
specified in the config file
"""


class Auctioneer(object):

    def __init__(self, api, ccu_store, **kwargs):

        logging.debug("Starting Auctioneer")

        self.api = api
        self.ccu_store = ccu_store
        self.robot_ids = kwargs.get('robot_ids', list())
        stp_solver = kwargs.get('stp_solver', None)
        stp = STP(stp_solver)
        self.alternative_timeslots = kwargs.get('alternative_timeslots', False)
        round_time = kwargs.get('round_time', 0)
        self.round_time = timedelta(seconds=round_time)

        # TODO: Read timetable from db
        self.timetable = Timetable(self.robot_ids, stp)

        self.tasks_to_allocate = dict()
        self.allocations = list()
        self.waiting_for_user_confirmation = list()
        self.round = Round()

    def __str__(self):
        to_print = "Auctioneer"
        to_print += '\n'
        to_print += "Groups {}".format(self.api.interfaces[0].groups())
        return to_print

    def run(self):
        if self.tasks_to_allocate and self.round.finished:
            self.announce_task()

        if self.round.opened and self.round.time_to_close():
            try:
                round_result = self.round.get_result()
                allocation = self.process_allocation(round_result)
                allocated_task, winner_robot_ids = allocation
                for robot_id in winner_robot_ids:
                    self.announce_winner(allocated_task, robot_id)

            except NoAllocation as exception:
                logging.exception("No allocation made in round %s ", exception.round_id)
                self.round.finish()

            except AlternativeTimeSlot as exception:
                self.process_alternative_allocation(exception)
                self.round.finish()

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

    def process_alternative_allocation(self, exception):
        task_id = exception.task_id
        robot_id = exception.robot_id
        alternative_start_time = exception.alternative_start_time
        logging.exception("Alternative timeslot for task %s: robot %s, alternative start time: %s ", task_id, robot_id,
                          alternative_start_time)

        alternative_allocation = (task_id, [robot_id], alternative_start_time)
        self.waiting_for_user_confirmation.append(alternative_allocation)

    def allocate(self, tasks):
        if isinstance(tasks, list):
            for task in tasks:
                self.tasks_to_allocate[task.id] = task
            logging.debug('Auctioneer received a list of tasks')
        else:
            self.tasks_to_allocate[tasks.id] = tasks
            logging.debug('Auctioneer received one task')

    def announce_task(self):

        round_ = {'tasks_to_allocate': self.tasks_to_allocate,
                  'round_time': self.round_time,
                  'n_robots': len(self.robot_ids),
                  'alternative_timeslots': self.alternative_timeslots}

        self.round = Round(**round_)

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
        self.api.publish(task_announcement, groups=['TASK-ALLOCATION'])

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
        self.api.publish(allocation, groups=['TASK-ALLOCATION'])

