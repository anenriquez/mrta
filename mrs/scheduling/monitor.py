import logging

from pymodm.errors import DoesNotExist
from ropod.structs.status import ActionStatus, TaskStatus as TaskStatusConst

from mrs.db.models.task import Task
from mrs.exceptions.execution import InconsistentAssignment
from mrs.exceptions.execution import InconsistentSchedule
from mrs.exceptions.execution import MissingDispatchableGraph
from mrs.messages.dispatch_queue_update import DispatchQueueUpdate
from mrs.scheduling.scheduler import Scheduler


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
        self.stn = self.stp_solver.get_stn()
        self.dispatchable_graph = self.stp_solver.get_stn()
        self.zero_timepoint = None
        self.queue_update_received = False

        self.scheduler = Scheduler(self.stp_solver, self.robot_id, self.dispatchable_graph, self.stn, time_resolution)
        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def schedule(self, task):
        task_position = self.stn.get_task_position(task.task_id)
        if task_position is None:
            self.logger.error("The STN does not include task %s", task.task_id)
            raise MissingDispatchableGraph(self.robot_id)
        else:
            try:
                scheduled_task = self.scheduler.schedule(task, self.zero_timepoint)
                self.logger.info("Task %s scheduled to start at %s", task.task_id, task.start_time)
                self.logger.debug("STN %s", self.stn)
                return scheduled_task

            except InconsistentSchedule as e:
                raise InconsistentSchedule(e.earliest_time, e.latest_time)

    def assign_timepoint(self, assigned_time, task_id, node_type):
        self.logger.debug("Assigning time %s to task %s timepoint %s", assigned_time, task_id, node_type)
        try:
            self.scheduler.assign_timepoint(assigned_time, task_id, node_type)
            self.logger.debug("STN with assigned value %s", self.stn)
        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, task_id)
            self.stn.assign_timepoint(e.assigned_time, e.task_id, e.node_type)
            self.logger.debug("STN with assigned value %s", self.stn)
            raise InconsistentAssignment(e.assigned_time, e.task_id, e.node_type)

    def get_next_task(self, task):
        task_last_node = self.stn.get_task_node_ids(task.task_id)[-1]
        if self.stn.has_node(task_last_node + 1):
            next_task_id = self.stn.nodes[task_last_node + 1]['data'].task_id
            try:
                next_task = Task.get_task(next_task_id)
            except DoesNotExist:
                self.logger.warning("Task %s is not in db", next_task_id)
                next_task = Task.create_new(task_id=next_task_id)
            return next_task

    def is_next_task_late(self, task, next_task):
        last_completed_action = None
        mean = 0
        variance = 0

        for action_progress in task.status.progress.actions:
            if action_progress.status == ActionStatus.COMPLETED:
                last_completed_action = action_progress.action

            elif action_progress.status == ActionStatus.ONGOING or action_progress.status == ActionStatus.PLANNED:
                mean += action_progress.action.estimated_duration.mean
                variance += action_progress.action.estimated_duration.variance

        estimated_duration = mean + 2*round(variance ** 0.5, 3)
        self.logger.debug("Remaining estimated task duration: %s ", estimated_duration)

        if last_completed_action:
            start_node, finish_node = last_completed_action.get_node_names()
            last_time = self.stn.get_time(task.task_id, finish_node)
        else:
            last_time = self.stn.get_time(task.task_id, 'start')

        estimated_start_time = last_time + estimated_duration
        self.logger.debug("Estimated start time of next task: %s ", estimated_start_time)

        latest_start_time = self.dispatchable_graph.get_time(next_task.task_id, 'start', False)
        self.logger.debug("Latest permitted start time of next task: ", latest_start_time)

        if latest_start_time < estimated_start_time:
            self.logger.debug("Next task is at risk")
            return True
        else:
            self.logger.debug("Next is at risk")
            return False

    def update_temporal_graph(self, temporal_graph):
        tasks = list()
        new_task_ids = temporal_graph.get_tasks()

        scheduled_tasks = [task.task_id for task in Task.get_tasks_by_status(TaskStatusConst.SCHEDULED) if task]
        ongoing_tasks = [task.task_id for task in Task.get_tasks_by_status(TaskStatusConst.ONGOING) if task]

        for i, task_id in enumerate(new_task_ids):
            if task_id in scheduled_tasks or ongoing_tasks:
                # Keep current version of task
                tasks.append(self.get_task_graph(self.dispatchable_graph, task_id))
            else:
                # Add task from d-graph update
                tasks.append(self.get_task_graph(temporal_graph, task_id))

        temporal_graph = self.stp_solver.get_stn()
        for task_graph in tasks:
            temporal_graph.add_nodes_from(task_graph.nodes(data=True))
            temporal_graph.add_edges_from(task_graph.edges(data=True))

        for i in temporal_graph.nodes():
            if i != 0 and temporal_graph.has_node(i+1) and not temporal_graph.has_edge(i, i+1):
                temporal_graph.add_constraint(i, i+1)

        return temporal_graph

    @staticmethod
    def get_task_graph(graph, task_id):
        node_ids = graph.get_task_node_ids(task_id)
        node_ids.insert(0, 0)
        task_graph = graph.subgraph(node_ids)
        return task_graph

    def remove_task(self, task_id):
        task_node_ids = self.stn.get_task_node_ids(task_id)
        self.stn.remove_node_ids(task_node_ids)
        self.dispatchable_graph.remove_node_ids(task_node_ids)
        self.logger.debug("STN: %s ", self.stn)
        self.logger.debug("Dispatchable graph: %s ", self.dispatchable_graph)

    def execute_timepoint(self, task_id, node_type):
        self.logger.critical("Execute task %s node %s", task_id, node_type)
        self.stn.execute_timepoint(task_id, node_type)
        print("STN:",  self.stn)

    def execute_edge(self, task_id, start_node, finish_node):
        self.logger.critical("Execute task %s edge between %s and %s", task_id, start_node, finish_node)
        start_node_idx, finish_node_idx = self.stn.get_edge_nodes_idx(task_id, start_node, finish_node)
        self.stn.execute_edge(start_node_idx, finish_node_idx)
        print("STN:",  self.stn)

    def remove_old_timepoints(self):
        self.logger.critical("Remove old timepoints")
        self.stn.remove_old_timepoints()

    def dispatch_queue_update_cb(self, msg):
        payload = msg['payload']
        self.logger.critical("Received dispatch queue update")
        d_graph_update = DispatchQueueUpdate.from_payload(payload)
        self.zero_timepoint = d_graph_update.zero_timepoint

        stn_cls = self.stp_solver.get_stn()

        stn = stn_cls.from_dict(d_graph_update.stn)
        self.stn = stn
        self.scheduler.stn = self.stn

        dispatchable_graph = stn_cls.from_dict(d_graph_update.dispatchable_graph)
        self.dispatchable_graph = dispatchable_graph
        self.scheduler.dispatchable_graph = self.dispatchable_graph

        self.logger.debug("STN update %s", self.stn)
        self.logger.debug("Dispatchable graph update %s", self.dispatchable_graph)
        self.queue_update_received = True



