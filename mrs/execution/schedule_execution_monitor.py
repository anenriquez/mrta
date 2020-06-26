import logging

from fmlib.models.tasks import TransportationTask as Task
from pymodm.errors import DoesNotExist
from ropod.structs.status import TaskStatus as TaskStatusConst

from mrs.exceptions.execution import InconsistentAssignment
from mrs.exceptions.execution import InconsistentSchedule
from mrs.messages.d_graph_update import DGraphUpdate
from mrs.messages.task_status import TaskStatus
from mrs.timetable.monitor import TimetableMonitorBase


class ScheduleExecutionMonitor(TimetableMonitorBase):

    def __init__(self, robot_id, timetable, scheduler, delay_recovery, **kwargs):
        """ Includes methods to monitor the schedule of a robot's allocated tasks
        """
        super().__init__(timetable=timetable, **kwargs)
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

    def process_task_status(self, task_status, timestamp):
        if self.robot_id == task_status.robot_id:
            self.send_task_status(task_status, timestamp)
            task = Task.get_task(task_status.task_id)

            if task_status.task_status == TaskStatusConst.ONGOING:
                self.update_timetable(task, task_status.robot_id, task_status.task_progress, timestamp)

            if task_status.task_status == TaskStatusConst.COMPLETED:
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
                self.preempt(task)

    def _update_timepoint(self, task, timetable, r_assigned_time, node_id, task_progress):
        is_consistent = True
        try:
            self.timetable.assign_timepoint(r_assigned_time, node_id)
        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s node_type %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, e.task_id, e.node_type)
            self.timetable.stn.assign_timepoint(e.assigned_time, node_id, force=True)
            is_consistent = False

        self.timetable.stn.execute_timepoint(node_id)
        self._update_edges(task, timetable)

        if not self.d_graph_watchdog:
            self.recover(task, task_progress, r_assigned_time, is_consistent)

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

    def send_task_status(self, task_status, timestamp=None):
        self.logger.debug("Sending task status for task %s", task_status.task_id)
        msg = self.api.create_message(task_status)
        if timestamp:
            msg["header"]["timestamp"] = timestamp.isoformat()
        self.api.publish(msg, groups=["TASK-ALLOCATION"])

    def send_task(self, task):
        self.logger.debug("Sending task %s to executor", task.task_id)
        task_msg = self.api.create_message(task)
        self.api.publish(task_msg, peer='executor_' + self.robot_id)

    def run(self):
        """ Gets the earliest task assigned to this robot and calls the ``process_task`` method
        for further processing
        """
        try:
            tasks = Task.get_tasks_by_robot(self.robot_id)
            if tasks and self.task is None:
                earliest_task = Task.get_earliest_task(tasks)
                if earliest_task:
                    self.process_task(earliest_task)
        except DoesNotExist:
            pass

    def process_task(self, task):
        task_status = task.get_task_status(task.task_id)

        if task_status.status == TaskStatusConst.DISPATCHED and self.timetable.has_task(task.task_id):
            self.schedule(task)

        # For real-time execution add is_executable condition
        if task_status.status == TaskStatusConst.SCHEDULED:
            self.send_task(task)
            self.task = task
