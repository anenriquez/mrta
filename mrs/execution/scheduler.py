import logging
from datetime import timedelta

import numpy as np
from ropod.structs.status import TaskStatus as TaskStatusConst

from mrs.exceptions.execution import InconsistentAssignment
from mrs.exceptions.execution import InconsistentSchedule
from mrs.messages.assignment_update import Assignment


class Scheduler(object):
    def __init__(self, robot_id, timetable, time_resolution):
        self.robot_id = robot_id
        self.timetable = timetable
        self.time_resolution = time_resolution
        self.logger = logging.getLogger("mrs.scheduler")
        self.logger.debug("Scheduler initialized %s", self.robot_id)

    def get_times(self, earliest_time, latest_time):
        start_times = list(np.arange(earliest_time, latest_time + self.time_resolution, self.time_resolution))
        if start_times[-1] > latest_time:
            start_times.pop()
        if len(start_times) < 2:
            start_times = [earliest_time, latest_time]
        return start_times

    def schedule(self, task):
        earliest_start_time = self.timetable.dispatchable_graph.get_time(task.task_id, lower_bound=True)
        latest_start_time = self.timetable.dispatchable_graph.get_time(task.task_id, lower_bound=False)
        start_times = self.get_times(earliest_start_time, latest_start_time)

        for start_time in start_times:
            self.logger.debug("Scheduling task %s to start at %s", task.task_id, start_time)
            try:
                self.timetable.assign_timepoint(start_time, task.task_id, "start")
                delivery_time = self.timetable.dispatchable_graph.get_time(task.task_id, 'delivery', lower_bound=False)

                schedule = {'start_time': (self.timetable.zero_timepoint + timedelta(seconds=start_time)).to_datetime(),
                            'finish_time': (self.timetable.zero_timepoint + timedelta(seconds=delivery_time)).to_datetime()}

                task.update_schedule(schedule)
                task.update_status(TaskStatusConst.SCHEDULED)

                assignment = Assignment(task.task_id, start_time, "start", is_consistent=True)

                return assignment

            except InconsistentAssignment as e:
                self.logger.warning("Task %s could not be scheduled at %s", e.task_id, e.assigned_time)

        self.logger.warning("Task %s could not be scheduled between %s and %s", task.task_id,
                            earliest_start_time, latest_start_time)
        raise InconsistentSchedule(earliest_start_time, latest_start_time)
