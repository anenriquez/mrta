import logging

from ropod.utils.timestamp import TimeStamp as ts
from mrs.task_execution.dispatching.scheduler import Scheduler
from mrs.timetable import Timetable
from stn.stp import STP
from mrs.exceptions.task_allocation import NoSTPSolution


class Dispatcher(object):

    def __init__(self, robot_id, ccu_store, task_cls, stp_solver):
        self.id = robot_id
        self.ccu_store = ccu_store
        self.task_cls = task_cls
        self.stp = STP(stp_solver)
        self.stp_solver = stp_solver
        self.scheduler = Scheduler(robot_id, ccu_store, self.stp)

        self.timetable = self.get_timetable()

        # corrective measure
        # TODO: get this info from the config file
        self.reschedule = True
        self.reallocate = False

    def get_timetable(self):
        timetable_dict = self.ccu_store.get_timetable(self.id)
        if timetable_dict is None:
            return
        self.timetable = Timetable.from_dict(timetable_dict, self.stp)
        return self.timetable

    # TODO: Add callback to receive

    def run(self):
        self.get_timetable()
        task = self.get_earliest_task()
        if task:
            self.check_earliest_task_status(task)

    def check_earliest_task_status(self, task):
        # task is allocated
        if task.status.status == 2:
            self.schedule_task(task)

        # task is completed
        elif task.status.status == 6:
            if self.stp_solver == 'drea':
                self.recompute_timetable(task)
            self.scheduler.reset_schedule()

        # task is delayed and corrective measure reschedule is active
        elif task.status.status == 5 and self.reschedule:
            self.recompute_timetable(task)

        elif task.status.status == 3 and self.time_to_dispatch():
            self.dispatch()

    def get_earliest_task(self):
        task_id = self.timetable.get_earliest_task_id()
        if task_id:
            task_dict = self.ccu_store.get_task(task_id)
            task = self.task_cls.from_dict(task_dict)
            return task

    def schedule_task(self, task):
        print("Scheduling task")
        self.scheduler.schedule_task(task, self.timetable)
        self.get_timetable()

    def recompute_timetable(self, task):
        try:
            self.timetable.solve_stp()

            logging.debug("Dispatchable graph %s: ", self.timetable.dispatchable_graph)
            logging.debug("Robustness Metric %s: ", self.timetable.robustness_metric)

        except NoSTPSolution:
            logging.exception("The stp solver could not solve the problem")
            self.update_task_status(task, 7)   # ABORTED
            self.timetable.remove_task(task)

    def update_task_status(self, task, status):
        task.status.status = status
        logging.debug("Updating task status to %s", task.status.status)
        self.ccu_store.update_task(task)

    def time_to_dispatch(self):
        current_time = ts.get_time_stamp()
        if current_time < self.scheduler.navigation_start_time:
            return False
        return True

    def dispatch(self):
        current_time = ts.get_time_stamp()
        print("Dispatching task at: ", current_time)










