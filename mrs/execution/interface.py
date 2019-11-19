import logging
from fmlib.models.tasks import Task
from mrs.dispatching.d_graph_update import DGraphUpdate
from ropod.structs.task import TaskStatus as TaskStatusConst
from mrs.scheduling.monitor import ScheduleMonitor
import networkx as nx
from stn.stn import STN
from ropod.utils.timestamp import TimeStamp


class ExecutorInterface:
    def __init__(self, robot_id,
                 stp_solver,
                 allocation_method,
                 corrective_measure,
                 **kwargs):
        self.robot_id = robot_id
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')
        self.schedule_monitor = ScheduleMonitor(robot_id,
                                                stp_solver,
                                                allocation_method,
                                                corrective_measure)
        self.queued_tasks = list()
        self.dispatchable_graph = None
        self.zero_timepoint = None
        self.logger = logging.getLogger("mrs.executor.interface.%s" % self.robot_id)
        self.logger.debug("Executor interface initialized %s", self.robot_id)

    def execute(self, task_id):
        self.logger.debug("Starting execution of task %s", task_id)
        task = Task.get_task(task_id)
        task.update_status(TaskStatusConst.ONGOING)

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

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        self.logger.debug("Received task %s", task.task_id)
        if self.robot_id in task.assigned_robots:
            self.queued_tasks.append(task)

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


