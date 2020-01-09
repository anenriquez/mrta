import logging
from datetime import timedelta

import numpy as np
from stn.methods.fpc import get_minimal_network

from mrs.exceptions.execution import InconsistentAssignment
from mrs.exceptions.execution import InconsistentSchedule
from mrs.messages.assignment_update import Assignment


class Scheduler(object):
    def __init__(self, stp_solver, robot_id, dispatchable_graph, stn, time_resolution):
        self.stp_solver = stp_solver
        self.robot_id = robot_id
        self.dispatchable_graph = dispatchable_graph
        self.stn = stn

        self.assignments = list()

        self.time_resolution = time_resolution
        self.logger = logging.getLogger("mrs.scheduler")

        self.logger.debug("Scheduler initialized %s", self.robot_id)

    def clean_assignments(self):
        self.assignments = list()

    def assign_timepoint(self, assigned_time, task_id, node_type):
        minimal_network = get_minimal_network(self.stn)

        if minimal_network:
            minimal_network.assign_timepoint(assigned_time, task_id, node_type)
            if self.stp_solver.is_consistent(minimal_network):
                self.stn.assign_timepoint(assigned_time, task_id, node_type)
                self.assignments.append(Assignment(task_id, assigned_time, node_type))
                return
        raise InconsistentAssignment(assigned_time, task_id, node_type)

    def get_times(self, earliest_time, latest_time):
        start_times = list(np.arange(earliest_time, latest_time + self.time_resolution, self.time_resolution))
        if start_times[-1] > latest_time:
            start_times.pop()
        if len(start_times) < 2:
            start_times = [earliest_time, latest_time]
        return start_times

    def schedule(self, task, zero_timepoint):
        earliest_start_time = self.dispatchable_graph.get_time(task.task_id, lower_bound=True)
        latest_start_time = self.dispatchable_graph.get_time(task.task_id, lower_bound=False)
        start_times = self.get_times(earliest_start_time, latest_start_time)

        for start_time in start_times:
            self.logger.debug("Scheduling task %s to start at %s", task.task_id, start_time)
            try:
                self.assign_timepoint(start_time, task.task_id, "start")
                task.start_time = (zero_timepoint + timedelta(seconds=start_time)).to_datetime()
                return task
            except InconsistentAssignment as e:
                self.logger.warning("Task %s could not be scheduled at %s", e.task_id, e.assigned_time)

        self.logger.warning("Task %s could not be scheduled between %s and %s", task.task_id,
                            earliest_start_time, latest_start_time)
        raise InconsistentSchedule(earliest_start_time, latest_start_time)
