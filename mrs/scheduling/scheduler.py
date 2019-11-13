import logging
from datetime import timedelta

from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst
from ropod.utils.timestamp import TimeStamp

from mrs.exceptions.execution import InconsistentSchedule


class Scheduler(object):
    def __init__(self, timetable, stp_solver, robot_id, freeze_window, n_tasks_sub_graph):
        self.timetable = timetable
        self.stp_solver = stp_solver
        self.robot_id = robot_id
        self.freeze_window = timedelta(seconds=freeze_window)
        self.n_tasks_sub_graph = n_tasks_sub_graph
        self.logger = logging.getLogger("mrs.scheduler")
        self.is_scheduling = False

        self.logger.debug("Scheduler initialized %s", self.robot_id)

    def is_schedulable(self, start_time):
        current_time = TimeStamp()
        if start_time.get_difference(current_time) < self.freeze_window:
            self.is_scheduling = True
            return True

        return False

    def schedule(self, task_id):
        r_start_time = self.timetable.get_r_time(task_id)
        start_time = self.timetable.get_start_time(task_id)
        finish_time = self.timetable.get_finish_time(task_id)
        sub_stn = self.timetable.stn.get_subgraph(self.n_tasks_sub_graph)
        try:
            self.timetable.assign_timepoint(sub_stn, r_start_time)
            task = Task.get_task(task_id)

            task_schedule = {"start_time": start_time.to_datetime(),
                             "finish_time": finish_time.to_datetime()}

            task.update_schedule(task_schedule)
            task.update_status(TaskStatusConst.SCHEDULED)
            self.logger.debug("Scheduling task %s to start at %s", task_id, start_time)

        except InconsistentSchedule:
            self.logger.warning("Task %s could not be scheduled at %s", task_id, start_time)
            # TODO: Trigger task re-allocation

        self.is_scheduling = False

