import logging
from datetime import timedelta

import numpy as np
from stn.methods.fpc import get_minimal_network

from mrs.exceptions.execution import InconsistentSchedule


class Scheduler(object):
    def __init__(self, stp_solver, robot_id, time_resolution):
        self.stp_solver = stp_solver
        self.robot_id = robot_id
        self.time_resolution = time_resolution
        self.logger = logging.getLogger("mrs.scheduler")
        self.is_scheduling = False

        self.logger.debug("Scheduler initialized %s", self.robot_id)

    def assign_timepoint(self, assigned_time, dispatchable_graph, task_id, node_type):
        minimal_network = get_minimal_network(dispatchable_graph)

        if minimal_network:
            minimal_network.assign_timepoint(assigned_time, task_id, node_type)
            if self.stp_solver.is_consistent(minimal_network):
                dispatchable_graph.assign_timepoint(assigned_time, task_id, node_type)
                return dispatchable_graph
        self.logger.debug("Task %s could not be scheduled at %s", task_id, assigned_time)
        return None

    def get_times(self, earliest_time, latest_time):
        start_times = list(np.arange(earliest_time, latest_time + self.time_resolution, self.time_resolution))
        if start_times[-1] > latest_time:
            start_times.pop()
        if len(start_times) < 2:
            start_times = [earliest_time, latest_time]
        return start_times

    def schedule(self, task, dispatchable_graph, zero_timepoint):
        earliest_start_time = dispatchable_graph.get_time(task.task_id, lower_bound=True)
        latest_start_time = dispatchable_graph.get_time(task.task_id, lower_bound=False)
        start_times = self.get_times(earliest_start_time, latest_start_time)

        for start_time in start_times:
            self.logger.debug("Scheduling task %s to start at %s", task.task_id, start_time)
            new_dispatchable_graph = self.assign_timepoint(start_time, dispatchable_graph, task.task_id, "start")
            if new_dispatchable_graph:
                task.start_time = (zero_timepoint + timedelta(seconds=start_time)).to_datetime()
                return task, new_dispatchable_graph

        self.logger.warning("Task %s could not be scheduled between %s and %s", task.task_id,
                            earliest_start_time, latest_start_time)
        raise InconsistentSchedule(earliest_start_time, latest_start_time)



