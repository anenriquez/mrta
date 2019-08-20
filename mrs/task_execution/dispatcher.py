import logging
import time
import uuid

from ropod.utils.timestamp import TimeStamp as ts
from stn.stp import STP
from importlib import import_module

from mrs.db_interface import DBInterface
from mrs.exceptions.task_allocation import NoSTPSolution
from mrs.exceptions.task_execution import InconsistentSchedule
from mrs.structs.task import TaskStatus
from mrs.structs.timetable import Timetable
from mrs.task_execution.scheduler import Scheduler


class Dispatcher(object):

    def __init__(self, robot_id, api, robot_store, task_type,
                 stp_solver, corrective_measure, freeze_window):

        self.id = robot_id
        self.api = api
        self.db_interface = DBInterface(robot_store)

        task_class_path = task_type.get('class', 'mrs.structs.task')
        self.task_cls = getattr(import_module(task_class_path), 'Task')

        self.stp = STP(stp_solver)
        self.stp_solver = stp_solver

        self.corrective_measure = corrective_measure
        self.freeze_window = freeze_window

        self.scheduler = Scheduler(robot_store, self.stp)

        timetable = self.db_interface.get_timetable(self.id, self.stp)
        if timetable is None:
            timetable = Timetable(self.stp, robot_id)
        self.timetable = timetable

    def run(self):
        self.timetable = self.db_interface.get_timetable(self.id, self.stp)
        if self.timetable is not None:
            task = self.get_earliest_task()
            if task is not None:
                self.check_earliest_task_status(task)

    def check_earliest_task_status(self, task):
        if task.status.status == TaskStatus.ALLOCATED:
            self.schedule_task(task)

        elif task.status.status == TaskStatus.COMPLETED:
            if self.stp_solver == 'drea':
                self.recompute_timetable(task)
            self.scheduler.reset_schedule(self.timetable)

        elif task.status.status == TaskStatus.ONGOING and task.status.delayed:
            self.apply_corrective_measure(task)

        elif task.status.status == TaskStatus.SCHEDULED and self.time_to_dispatch():
            self.dispatch(task)

    def apply_corrective_measure(self, task):
        if self.corrective_measure == 're-schedule':
            self.recompute_timetable(task)

        elif self.corrective_measure == 're-allocate':
            self.scheduler.reset_schedule(self.timetable)
            self.request_reallocation(task)

        else:
            logging.debug("Not applying corrective measure")

    def get_earliest_task(self):
        task_id = self.timetable.get_earliest_task_id()
        if task_id:
            task_dict = self.db_interface.get_task(task_id)
            task = self.task_cls.from_dict(task_dict)
            return task

    def schedule_task(self, task):
        print("Scheduling task")

        navigation_start = self.timetable.dispatchable_graph.get_task_navigation_start_time(task.id)
        current_time = ts.get_time_stamp()

        # Schedule the task freeze_window time before the navigation start and freeze it
        #  i.e., the task cannot longer change position in the dispatchable graph
        if (navigation_start - current_time) <= self.freeze_window:
            try:
                self.scheduler.schedule_task(task, navigation_start, self.timetable)
            except InconsistentSchedule as e:
                logging.exception("Task %s could not be scheduled.", e.task)
                if self.corrective_measure == 're-allocate':
                    self.request_reallocation(task)

        self.timetable = self.db_interface.get_timetable(self.id, self.stp)

    def recompute_timetable(self, task):
        try:
            self.timetable.solve_stp()

            logging.debug("Dispatchable graph %s: ", self.timetable.dispatchable_graph)
            logging.debug("Robustness Metric %s: ", self.timetable.robustness_metric)

        except NoSTPSolution:
            logging.exception("The stp solver could not solve the problem")
            self.db_interface.update_task_status(task, TaskStatus.FAILED)
            self.timetable.remove_task()

    def time_to_dispatch(self):
        current_time = ts.get_time_stamp()
        if current_time < self.scheduler.navigation_start_time:
            return False
        return True

    def dispatch(self, task):
        current_time = ts.get_time_stamp()
        print("Dispatching task at: ", current_time)

        logging.info("Dispatching task to robot %s", self.id)

        task_msg = dict()
        task_msg['header'] = dict()
        task_msg['payload'] = dict()
        task_msg['header']['type'] = 'TASK'
        task_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        task_msg['header']['msgId'] = str(uuid.uuid4())
        task_msg['header']['timestamp'] = int(round(time.time()) * 1000)

        task_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'
        task_msg['payload']['task'] = task.to_dict()

        self.db_interface.update_task_status(task, TaskStatus.SHIPPED)
        self.timetable.remove_task()

        self.api.publish(task_msg, groups=['ROPOD'])

    def request_reallocation(self, task):
        self.db_interface.update_task_status(task, TaskStatus.UNALLOCATED)  # ABORTED
        task_msg = dict()
        task_msg['header'] = dict()
        task_msg['payload'] = dict()
        task_msg['header']['type'] = 'TASK'
        task_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        task_msg['header']['msgId'] = str(uuid.uuid4())
        task_msg['header']['timestamp'] = int(round(time.time()) * 1000)

        task_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'
        task_msg['payload']['task'] = task.to_dict()

        self.api.publish(task_msg, groups=['TASK-ALLOCATION'])










