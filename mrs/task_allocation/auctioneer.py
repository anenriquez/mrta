import logging
import time
from datetime import datetime
from datetime import timedelta
from importlib import import_module

from ropod.utils.timestamp import TimeStamp
from stn.stp import STP

from mrs.db_interface import DBInterface
from mrs.exceptions.task_allocation import AlternativeTimeSlot
from mrs.exceptions.task_allocation import NoAllocation
from mrs.structs.allocation import TaskAnnouncement, Allocation
from mrs.structs.task import TaskStatus
from mrs.structs.timetable import Timetable
from mrs.task_allocation.round import Round

""" Implements a variation of the the TeSSI algorithm using the bidding_rule 
specified in the config file
"""


class Auctioneer(object):

    def __init__(self, robot_ids, ccu_store, api, stp_solver,
                 task_type, allocation_method, round_time=5, **kwargs):

        self.logger = logging.getLogger("mrs.auctioneer")

        self.robot_ids = robot_ids
        self.db_interface = DBInterface(ccu_store)
        self.api = api
        self.stp = STP(stp_solver)

        self.allocation_method = allocation_method
        self.round_time = timedelta(seconds=round_time)
        self.alternative_timeslots = kwargs.get('alternative_timeslots', False)

        task_class_path = task_type.get('class', 'mrs.structs.task')
        self.task_cls = getattr(import_module(task_class_path), 'Task')
        self.logger.debug("Auctioneer started")

        # TODO: Inititalize the timetables in the loader? and read the timetables here
        self.timetables = dict()
        for robot_id in robot_ids:
            timetable = Timetable.get_timetable(self.db_interface, robot_id, self.stp)
            self.db_interface.add_timetable(timetable)
            self.timetables[robot_id] = timetable

        self.tasks_to_allocate = dict()
        self.allocations = list()
        self.waiting_for_user_confirmation = list()
        self.round = Round()

        # TODO: Update ztp
        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        self.ztp = TimeStamp(stamp_time=today_midnight)

    def __str__(self):
        to_print = "Auctioneer"
        to_print += '\n'
        to_print += "Groups {}".format(self.api.interfaces[0].groups())
        return to_print

    def check_db(self):
        tasks_dict = self.db_interface.get_tasks()
        for task_id, task_dict in tasks_dict.items():
            task = self.task_cls.from_dict(task_dict)
            if task.status == TaskStatus.UNALLOCATED:
                self.add_task(task)

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
                self.logger.exception("No mrs made in round %s ", exception.round_id)
                self.round.finish()

            except AlternativeTimeSlot as exception:
                self.process_alternative_allocation(exception)
                self.round.finish()

    def process_allocation(self, round_result):

        task, robot_id, position, tasks_to_allocate = round_result

        allocation = (task.id, [robot_id])
        self.allocations.append(allocation)
        self.tasks_to_allocate = tasks_to_allocate

        self.logger.debug("Allocation: %s", allocation)
        self.logger.debug("Tasks to allocate %s", self.tasks_to_allocate)

        self.logger.debug("Updating task status to ALLOCATED")
        self.db_interface.update_task_status(task, TaskStatus.ALLOCATED)
        self.update_timetable(robot_id, task, position)

        return allocation

    def update_timetable(self, robot_id, task, position):
        timetable = self.db_interface.get_timetable(robot_id, self.stp)
        timetable.add_task_to_stn(task, self.ztp, position)
        print("STN: ", timetable.stn)
        timetable.solve_stp()

        # Update schedule to reflect the changes in the dispatchable graph
        if timetable.is_scheduled():
            # TODO: Request re-scheduling to the scheduler via pyre
            pass

        self.timetables.update({robot_id: timetable})
        self.db_interface.update_timetable(timetable)

        self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
        self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

    def process_alternative_allocation(self, exception):
        task_id = exception.task_id
        robot_id = exception.robot_id
        alternative_start_time = exception.alternative_start_time
        self.logger.exception("Alternative timeslot for task %s: robot %s, alternative start time: %s ", task_id, robot_id,
                          alternative_start_time)

        alternative_allocation = (task_id, [robot_id], alternative_start_time)
        self.waiting_for_user_confirmation.append(alternative_allocation)

    def add_task(self, task):
        self.tasks_to_allocate[task.id] = task
        self.db_interface.update_task(task)

    def allocate(self, tasks):
        if isinstance(tasks, list):
            for task in tasks:
                self.add_task(task)
            self.logger.debug('Auctioneer received a list of tasks')
        else:
            self.add_task(tasks)
            self.logger.debug('Auctioneer received one task')

    def announce_task(self):

        round_ = {'tasks_to_allocate': self.tasks_to_allocate,
                  'round_time': self.round_time,
                  'n_robots': len(self.robot_ids),
                  'alternative_timeslots': self.alternative_timeslots}

        self.round = Round(**round_)

        self.logger.info("Starting round: %s", self.round.id)
        self.logger.info("Number of tasks to allocate: %s", len(self.tasks_to_allocate))

        tasks = list(self.tasks_to_allocate.values())
        task_announcement = TaskAnnouncement(tasks, self.round.id, self.ztp)
        msg = self.api.create_message(task_announcement)

        self.logger.debug('task annoucement msg: %s', msg)

        self.logger.debug("Auctioneer announces tasks %s", [task_id for task_id, task in self.tasks_to_allocate.items()])

        self.round.start()
        self.api.publish(msg, groups=['TASK-ALLOCATION'])

    def send_timetable(self, robot_id):
        timetable = Timetable.get_timetable(self.db_interface, robot_id, self.stp)
        msg = self.api.create_message(timetable)
        self.api.publish(msg)

    def allocate_task_cb(self, msg):
        self.logger.debug("Task received")
        task_dict = msg['payload']['task']
        task = self.task_cls.from_dict(task_dict)
        self.add_task(task)

    def bid_cb(self, msg):
        bid = msg['payload']
        self.round.process_bid(bid)

    def finish_round_cb(self, msg):
        self.round.finish()

    def announce_winner(self, task_id, robot_id):
        allocation = Allocation(task_id, robot_id)
        msg = self.api.create_message(allocation)
        self.api.publish(msg, groups=['TASK-ALLOCATION'])

    def get_task_schedule(self, task_id, robot_id):
        # For now, returning the start navigation time from the dispatchable graph

        task_schedule = dict()

        timetable = self.timetables.get(robot_id)

        relative_start_navigation_time = timetable.dispatchable_graph.get_task_time(task_id, "navigation")
        relative_start_time = timetable.dispatchable_graph.get_task_time(task_id, "start")
        relative_latest_finish_time = timetable.dispatchable_graph.get_task_time(task_id, "finish", False)

        self.logger.debug("Current time %s: ", TimeStamp())
        self.logger.debug("ztp %s: ", self.ztp)
        self.logger.debug("Relative start navigation time: %s", relative_start_navigation_time)
        self.logger.debug("Relative start time: %s", relative_start_time)
        self.logger.debug("Relative latest finish time: %s", relative_latest_finish_time)

        start_navigation_time = self.ztp + timedelta(minutes=relative_start_navigation_time)
        start_time = self.ztp + timedelta(minutes=relative_start_time)
        finish_time = self.ztp + timedelta(minutes=relative_latest_finish_time)

        self.logger.debug("Start navigation of task %s: %s", task_id, start_navigation_time)
        self.logger.debug("Start of task %s: %s", task_id, start_time)
        self.logger.debug("Latest finish of task %s: %s", task_id, finish_time)

        task_schedule['start_time'] = start_navigation_time
        task_schedule['finish_time'] = finish_time

        return task_schedule


if __name__ == '__main__':

    from fleet_management.config.loader import Config
    config_file_path = '../../config/config.yaml'
    config = Config(config_file_path, initialize=True)
    auctioneer = config.configure_auctioneer(config.ccu_store)

    time.sleep(5)

    auctioneer.api.register_callbacks(auctioneer)

    try:
        auctioneer.api.start()
        while True:
            auctioneer.run()
            auctioneer.api.run()
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        print("Terminating auctioneer ...")
        auctioneer.api.shutdown()
        print("Exiting...")
