import logging

from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst

from mrs.exceptions.execution import InconsistentSchedule


class Scheduler(object):
    def __init__(self, timetable, stp_solver, robot_id):
        self.timetable = timetable
        self.stp_solver = stp_solver
        self.robot_id = robot_id
        self.logger = logging.getLogger("mrs.scheduler")
        self.is_scheduling = False

        self.logger.debug("Scheduler initialized %s", self.robot_id)

    def schedule(self, task_id):
        r_start_time = self.timetable.get_r_time(task_id)
        try:
            self.timetable.assign_timepoint(r_start_time, task_id, "navigation")
            start_time = self.timetable.get_start_time(task_id)
            pickup_time = self.timetable.get_pickup_time(task_id)
            finish_time = self.timetable.get_finish_time(task_id)
            task = Task.get_task(task_id)

            task_schedule = {"start_time": start_time.to_datetime(),
                             "pickup_time": pickup_time.to_datetime(),
                             "finish_time": finish_time.to_datetime()}

            task.update_schedule(task_schedule)
            task.update_status(TaskStatusConst.SCHEDULED)
            self.logger.debug(" Task %s scheduled \n "
                              "start time: %s \n"
                              "pickup time (latest): %s \n"
                              "finish time (latest) :%s",
                              task_id, start_time, pickup_time, finish_time)

        except InconsistentSchedule:
            self.logger.warning("Task %s could not be scheduled at %s", task_id, start_time)
            # TODO: Trigger task re-allocation

