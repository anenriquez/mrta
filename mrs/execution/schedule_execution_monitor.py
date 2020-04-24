import logging

from fmlib.models.tasks import TransportationTask as Task
from mrs.exceptions.execution import InconsistentAssignment
from mrs.messages.d_graph_update import DGraphUpdate
from mrs.messages.task_status import TaskStatus
from mrs.utils.time import relative_to_ztp
from ropod.structs.status import ActionStatus as ActionStatusConst, TaskStatus as TaskStatusConst
from ropod.utils.timestamp import TimeStamp
from mrs.exceptions.execution import InconsistentSchedule


class ScheduleExecutionMonitor:

    def __init__(self, robot_id, timetable, scheduler, delay_recovery, **kwargs):
        """ Includes methods to monitor the schedule of a robot's allocated tasks
        """
        self.robot_id = robot_id
        self.timetable = timetable
        self.timetable.fetch()
        self.scheduler = scheduler
        self.recovery_method = delay_recovery
        self.d_graph_watchdog = kwargs.get("d_graph_watchdog", False)
        self.api = kwargs.get("api")

        self.d_graph_update_received = False
        self.task = None

        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)
        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def configure(self, **kwargs):
        api = kwargs.get('api')
        if api:
            self.api = api

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        if self.robot_id in task.assigned_robots:
            self.logger.debug("Received task %s", task.task_id)
            task.update_status(TaskStatusConst.DISPATCHED)

    def d_graph_update_cb(self, msg):
        payload = msg['payload']
        self.logger.debug("Received DGraph update")
        d_graph_update = DGraphUpdate.from_payload(payload)
        d_graph_update.update_timetable(self.timetable)
        self.logger.debug("STN update %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph update %s", self.timetable.dispatchable_graph)
        self.d_graph_update_received = True

    def task_status_cb(self, msg):
        payload = msg['payload']
        timestamp = TimeStamp.from_str(msg["header"]["timestamp"]).to_datetime()
        task_status = TaskStatus.from_payload(payload)

        if self.robot_id == task_status.robot_id:

            task = Task.get_task(task_status.task_id)
            self.logger.debug("Received task status %s for task %s", task_status.task_status, task.task_id)

            self.logger.debug("Sending task status %s for task %s", task_status.task_status, task.task_id)
            self.api.publish(msg, groups=["TASK-ALLOCATION"])

            if task_status.task_status == TaskStatusConst.ONGOING:
                self.update_timetable(task, task_status.task_progress, timestamp)

            elif task_status.task_status == TaskStatusConst.COMPLETED:
                self.logger.debug("Completing execution of task %s", task.task_id)
                self.task = None

            task.update_status(task_status.task_status)

    def schedule(self, task):
        try:
            self.scheduler.schedule(task)
        except InconsistentSchedule:
            if "re-allocate" in self.recovery_method:
                self.re_allocate(task)
            else:
                self.abort(task)

    def update_timetable(self, task, task_progress, timestamp):
        r_assigned_time = relative_to_ztp(self.timetable.ztp, timestamp)
        first_action_id = task.plan[0].actions[0].action_id

        if task_progress.action_id == first_action_id and \
                task_progress.action_status.status == ActionStatusConst.ONGOING:
            node_id, node = self.timetable.stn.get_node_by_type(task.task_id, 'start')
            self.update_timepoint(task, task_progress, r_assigned_time, node, node_id)
        else:
            # An action could be associated to two nodes, e.g., between pickup and delivery there is only one action
            nodes = self.timetable.stn.get_nodes_by_action(task_progress.action_id)

            for node_id, node in nodes:
                if (node.node_type == 'pickup' and
                    task_progress.action_status.status == ActionStatusConst.ONGOING) or\
                        (node.node_type == 'delivery' and
                         task_progress.action_status.status == ActionStatusConst.COMPLETED):

                    self.update_timepoint(task, task_progress, r_assigned_time, node, node_id)

    def update_timepoint(self, task, task_progress, r_assigned_time, node, node_id):
        is_consistent = True
        self.logger.debug("Assigning time %s to task %s timepoint %s", r_assigned_time, node.task_id,
                          node.node_type)
        try:
            self.timetable.assign_timepoint(r_assigned_time, node_id)

        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s node_type %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, e.task_id, e.node_type)
            self.timetable.stn.assign_timepoint(e.assigned_time, node_id, force=True)
            is_consistent = False

        self.timetable.stn.execute_timepoint(node_id)
        nodes = self.timetable.stn.get_nodes_by_task(task.task_id)
        self._update_edge('start', 'pickup', nodes)
        self._update_edge('pickup', 'delivery', nodes)
        self.logger.debug("STN: \n %s",  self.timetable.stn)

        if not self.d_graph_watchdog:
            self.recover(task, task_progress, r_assigned_time, is_consistent)

    def _update_edge(self, start_node, finish_node, nodes):
        node_ids = [node_id for node_id, node in nodes if (node.node_type == start_node and node.is_executed) or
                    (node.node_type == finish_node and node.is_executed)]
        if len(node_ids) == 2:
            self.timetable.execute_edge(node_ids[0], node_ids[1])

    def recover(self, task, task_progress, r_assigned_time, is_consistent):
        """ Applies a recovery method (preventive or corrective) if needed.
        A preventive recovery prevents delay of next_task. Applied BEFORE current task becomes inconsistent
        A corrective recovery prevents delay of next task. Applied AFTER current task becomes inconsistent

        task (Task) : current task
        is_consistent (boolean): True if the last assignment was consistent, false otherwise
        """

        task_to_recover = self.recovery_method.recover(self.timetable, task, task_progress, r_assigned_time, is_consistent)

        if task_to_recover and self.recovery_method.name == "re-allocate":
            self.re_allocate(task_to_recover)

        elif task_to_recover and self.recovery_method.name == "preempt":
            self.preempt(task_to_recover)

    def re_allocate(self, task):
        self.logger.info("Trigger re-allocation of task %s", task.task_id)
        task.update_status(TaskStatusConst.UNALLOCATED)
        self.timetable.remove_task(task.task_id)
        task_status = TaskStatus(task.task_id, self.robot_id, TaskStatusConst.UNALLOCATED)
        self.send_task_status(task_status)

    def preempt(self, task):
        self.logger.info("Trigger preemption of task %s", task.task_id)
        task.update_status(TaskStatusConst.PREEMPTED)
        self.timetable.remove_task(task.task_id)
        task_status = TaskStatus(task.task_id, self.robot_id, TaskStatusConst.PREEMPTED)
        self.send_task_status(task_status)

    def send_task_status(self, task_status):
        self.logger.debug("Sending task status for task %s", task_status.task_id)
        msg = self.api.create_message(task_status)
        self.api.publish(msg, groups=["TASK-ALLOCATION"])

    def send_task(self, task):
        self.logger.debug("Sending task %s to executor", task.task_id)
        task_msg = self.api.create_message(task)
        self.api.publish(task_msg, peer='executor_' + self.robot_id)

    def process_tasks(self, tasks):
        for task in tasks:
            task_status = task.get_task_status(task.task_id)

            if task_status.status == TaskStatusConst.DISPATCHED and self.timetable.has_task(task.task_id):
                self.schedule(task)

            # For real-time execution add is_executable condition
            if task_status.status == TaskStatusConst.SCHEDULED:
                self.send_task(task)
                self.task = task
