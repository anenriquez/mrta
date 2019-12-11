import logging

from ropod.utils.timestamp import TimeStamp
from stn.stn import STN

from mrs.messages.dispatch_queue_update import DispatchQueueUpdate
from mrs.exceptions.execution import InconsistentSchedule
from mrs.exceptions.execution import MissingDispatchableGraph
from mrs.scheduling.scheduler import Scheduler
from mrs.db.models.task import TransportationTask as Task
from ropod.structs.task import TaskStatus as TaskStatusConst


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
                 time_resolution,
                 tasks):
        """ Includes methods to monitor the schedule of a robot's allocated tasks

       Args:

            robot_id (str):  id of the robot, e.g. ropod_001
            stp_solver (STP): Simple Temporal Problem object
            allocation_method (str): Name of the allocation method
            corrective_measure (str): Name of the corrective measure
        """
        self.robot_id = robot_id
        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)
        self.stp_solver = stp_solver
        self.corrective_measure = self.get_corrective_measure(allocation_method, corrective_measure)
        self.scheduler = Scheduler(self.stp_solver, self.robot_id, time_resolution)
        self.tasks = tasks
        self.dispatchable_graph = None
        self.zero_timepoint = None
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
            # TODO: Trigger reallocation of task
            raise InconsistentSchedule(e.earliest_time, e.latest_time)

    def assign_timepoint(self, assigned_time, task_id, node_type):
        self.logger.debug("Assigning time %s to task %s timepoint %s", assigned_time, task_id, node_type)
        dispatchable_graph = self.scheduler.assign_timepoint(assigned_time, self.dispatchable_graph, task_id, node_type)
        if dispatchable_graph:
            self.dispatchable_graph = dispatchable_graph
            self.logger.debug("Dispatchable graph with assigned value %s", self.dispatchable_graph)
            self.apply_corrective_measure(task_id, consistent=True)
        else:
            self.logger.warning("Assignment of time %s to task %s timepoint %s was not consistent",
                                assigned_time, task_id, node_type)
            self.apply_corrective_measure(task_id, consistent=False)

    def apply_corrective_measure(self, task_id, consistent):
        if not consistent and self.corrective_measure is None:
            # Abort next task
            pass

        elif not consistent and self.corrective_measure == 're-allocate':
            self.estimate_start_next_task()

        elif consistent and self.corrective_measure == 're-schedule':
            # Re-compute dispatchable graph
            pass

    def estimate_start_next_task(self):
        pass

    def update_dispatchable_graph(self, dispatchable_graph):
        tasks = list()
        new_task_ids = dispatchable_graph.get_tasks()

        scheduled_tasks = [task.task_id for task in Task.get_tasks_by_status(TaskStatusConst.SCHEDULED) if task]
        ongoing_tasks = [task.task_id for task in Task.get_tasks_by_status(TaskStatusConst.ONGOING) if task]

        for i, task_id in enumerate(new_task_ids):
            if task_id in scheduled_tasks or ongoing_tasks:
                # Keep current version of task
                tasks.append(self.get_task_graph(self.dispatchable_graph, task_id))
            else:
                # Add task from d-graph update
                tasks.append(self.get_task_graph(dispatchable_graph, task_id))

        stn = STN()
        for task_graph in tasks:
            stn.add_nodes_from(task_graph.nodes(data=True))
            stn.add_edges_from(task_graph.edges(data=True))

        for i in stn.nodes():
            if i != 0 and stn.has_node(i+1) and not stn.has_edge(i, i+1):
                stn.add_constraint(i, i+1)

        self.dispatchable_graph = stn

    @staticmethod
    def get_task_graph(graph, task_id):
        node_ids = graph.get_task_node_ids(task_id)
        node_ids.insert(0, 0)
        task_graph = graph.subgraph(node_ids)
        return task_graph

    def remove_task(self, task_id):
        node_id = self.dispatchable_graph.get_task_position(task_id)
        self.dispatchable_graph.remove_task(node_id)
        self.logger.debug("Dispatchable graph: %s ", self.dispatchable_graph)
        return node_id

    def dispatch_queue_update_cb(self, msg):
        payload = msg['payload']
        d_graph_update = DispatchQueueUpdate.from_payload(payload)
        self.zero_timepoint = TimeStamp.from_str(d_graph_update.zero_timepoint)
        dispatchable_graph = STN.from_dict(d_graph_update.dispatchable_graph)
        if self.dispatchable_graph:
            self.update_dispatchable_graph(dispatchable_graph)
        else:
            self.dispatchable_graph = dispatchable_graph
        self.logger.debug("Dispatchable graph update %s", self.dispatchable_graph)



