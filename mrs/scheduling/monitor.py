import logging

import networkx as nx
from ropod.utils.timestamp import TimeStamp
from stn.stn import STN

from mrs.dispatching.d_graph_update import DGraphUpdate
from mrs.scheduling.scheduler import Scheduler
from mrs.exceptions.execution import InconsistentSchedule
from mrs.exceptions.execution import MissingDispatchableGraph


class ScheduleMonitor:

    """ Maps allocation methods with their available corrective measures """

    corrective_measures = {'tessi': ['re-allocate'],
                           'tessi-srea': ['re-allocate'],
                           'tessi-drea': ['re-schedule'],
                           'tessi-dsc': ['re-allocate']
                           }

    def __init__(self, robot_id,
                 stp_solver,
                 allocation_method,
                 corrective_measure,
                 time_resolution):
        """ Includes methods to monitor the schedule of a robot's allocated tasks

       Args:

            robot_id (str):  id of the robot, e.g. ropod_001
            stp_solver (STP): Simple Temporal Problem object
            allocation_method (str): Name of the allocation method
            corrective_measure (str): Name of the corrective measure
        """
        self.robot_id = robot_id
        self.stp_solver = stp_solver
        self.corrective_measure = self.get_corrective_measure(allocation_method, corrective_measure)
        self.scheduler = Scheduler(self.stp_solver, self.robot_id, time_resolution)
        self.dispatchable_graph = None
        self.zero_timepoint = None
        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)
        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def get_corrective_measure(self, allocation_method, corrective_measure):
        available_corrective_measures = self.corrective_measures.get(allocation_method)
        if corrective_measure not in available_corrective_measures:
            self.logger.error("Corrective measure %s is not available for method %s", corrective_measure, allocation_method)
            raise ValueError(corrective_measure)

        return corrective_measure

    def schedule(self, task):
        try:
            if not self.dispatchable_graph:
                self.logger.error("The schedule monitor does not have a dispatchable graph")
                raise MissingDispatchableGraph(self.robot_id)

            scheduled_task, dispatchable_task = self.scheduler.schedule(task, self.dispatchable_graph, self.zero_timepoint)
            self.dispatchable_graph = dispatchable_task
            self.logger.info("Task %s scheduled to start at %s", task.task_id, task.start_time)
            self.logger.debug("Dispatchable graph %s", self.dispatchable_graph)
            return scheduled_task

        except InconsistentSchedule as e:
            # TODO: Trigger corrective measure
            raise InconsistentSchedule(e.earliest_time, e.latest_time)

    def update_dispatchable_graph(self, dispatchable_graph):
        current_task_ids = self.dispatchable_graph.get_tasks()
        new_task_ids = dispatchable_graph.get_tasks()

        for task_id in new_task_ids:
            if task_id not in current_task_ids:
                # Get graph with new task
                node_ids = dispatchable_graph.get_task_node_ids(task_id)
                node_ids.insert(0, 0)
                task_graph = dispatchable_graph.subgraph(node_ids)

                # Update dispatchable graph to include new task
                self.dispatchable_graph = nx.compose(self.dispatchable_graph, task_graph)

    def d_graph_update_cb(self, msg):
        self.logger.critical("Received d-graph-update")
        payload = msg['payload']
        d_graph_update = DGraphUpdate.from_payload(payload)
        self.zero_timepoint = TimeStamp.from_str(d_graph_update.zero_timepoint)
        dispatchable_graph = STN.from_dict(d_graph_update.dispatchable_graph)
        if self.dispatchable_graph:
            self.update_dispatchable_graph(dispatchable_graph)
        else:
            self.dispatchable_graph = dispatchable_graph



