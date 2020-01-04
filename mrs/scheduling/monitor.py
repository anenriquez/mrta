import logging

from mrs.db.models.task import Task
from mrs.exceptions.execution import InconsistentAssignment
from mrs.exceptions.execution import InconsistentSchedule
from mrs.exceptions.execution import MissingDispatchableGraph
from mrs.messages.dispatch_queue_update import DispatchQueueUpdate
from mrs.scheduling.scheduler import Scheduler
from ropod.structs.status import ActionStatus, TaskStatus as TaskStatusConst


class ScheduleMonitor:

    def __init__(self, robot_id, stp_solver, time_resolution):
        """ Includes methods to monitor the schedule of a robot's allocated tasks

       Args:

            robot_id (str):  id of the robot, e.g. ropod_001
            stp_solver (STP): Simple Temporal Problem object
        """
        self.robot_id = robot_id
        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)

        self.stp_solver = stp_solver
        self.scheduler = Scheduler(self.stp_solver, self.robot_id, time_resolution)

        self.dispatchable_graph = None
        self.zero_timepoint = None
        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def schedule(self, task):
        task_position = self.dispatchable_graph.get_task_position(task.task_id)
        if task_position is None:
            self.logger.error("The dispatchable graph does not include task %s", task.task_id)
            raise MissingDispatchableGraph(self.robot_id)
        else:
            try:
                scheduled_task, dispatchable_task = self.scheduler.schedule(task, self.dispatchable_graph, self.zero_timepoint)
                self.dispatchable_graph = dispatchable_task
                self.logger.info("Task %s scheduled to start at %s", task.task_id, task.start_time)
                self.logger.debug("Dispatchable graph %s", self.dispatchable_graph)
                return scheduled_task

            except InconsistentSchedule as e:
                raise InconsistentSchedule(e.earliest_time, e.latest_time)

    def assign_timepoint(self, assigned_time, task_id, node_type):
        self.logger.debug("Assigning time %s to task %s timepoint %s", assigned_time, task_id, node_type)
        try:
            self.dispatchable_graph = self.scheduler.assign_timepoint(assigned_time, self.dispatchable_graph, task_id, node_type)
            self.logger.debug("Dispatchable graph with assigned value %s", self.dispatchable_graph)
        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, task_id)
            self.dispatchable_graph = e.dispatchable_graph
            raise InconsistentAssignment(e.assigned_time, e.dispatchable_graph)

    def get_next_task(self, task):
        task_idx = self.dispatchable_graph.get_task_position(task.task_id)
        next_task_id = self.dispatchable_graph.get_task_id(task_idx+1)
        if next_task_id:
            next_task = Task.get_task(next_task_id)
            return next_task

    def is_next_task_late(self, task, next_task):
        mean = 0
        variance = 0
        for action_progress in task.status.progress.actions:
            if action_progress.status == ActionStatus.ONGOING or action_progress.status == ActionStatus.PLANNED:
                mean += action_progress.action.estimated_duration.mean
                variance += action_progress.action.estimated_duration.variance

        estimated_duration = mean + 2*round(variance ** 0.5, 3)
        estimated_start_time = self.dispatchable_graph.get_time(task.task_id, 'start') + estimated_duration

        latest_start_time = self.dispatchable_graph.get_time(next_task.task_id, 'start', False)

        if latest_start_time < estimated_start_time:
            return True

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

        stn = self.stp_solver.get_stn()
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
        self.zero_timepoint = d_graph_update.zero_timepoint
        stn = self.stp_solver.get_stn()
        dispatchable_graph = stn.from_dict(d_graph_update.dispatchable_graph)
        if self.dispatchable_graph:
            self.update_dispatchable_graph(dispatchable_graph)
        else:
            self.dispatchable_graph = dispatchable_graph
        self.logger.debug("Dispatchable graph update %s", self.dispatchable_graph)



