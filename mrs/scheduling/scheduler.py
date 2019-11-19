import logging
import numpy as np
from stn.methods.fpc import get_minimal_network
from mrs.exceptions.execution import InconsistentSchedule
from datetime import timedelta


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
        return None

    def schedule(self, task, dispatchable_graph, zero_timepoint):
        earliest_start_time = dispatchable_graph.get_time(task.task_id, lower_bound=True)
        latest_start_time = dispatchable_graph.get_time(task.task_id, lower_bound=False)
        start_times = np.arange(earliest_start_time, latest_start_time, self.time_resolution).tolist()

        for start_time in start_times:
            dispatchable_graph = self.assign_timepoint(start_time, dispatchable_graph, task.task_id, "navigation")
            if dispatchable_graph:
                task.start_time = (zero_timepoint + timedelta(minutes=start_time)).to_datetime()
                return task, dispatchable_graph

        self.logger.warning("Task %s could not be scheduled between %s and %s", task.task_id,
                            earliest_start_time, latest_start_time)
        raise InconsistentSchedule(earliest_start_time, latest_start_time)



