import logging
from datetime import timedelta

from fmlib.models.actions import Action
from ropod.structs.status import ActionStatus as ActionStatusConst, TaskStatus as TaskStatusConst

from mrs.exceptions.execution import InconsistentAssignment
from mrs.messages.d_graph_update import DGraphUpdate
from mrs.messages.recover_task import RecoverTask
from mrs.messages.task_status import TaskProgress


class ScheduleExecutionMonitor:

    def __init__(self, robot_id, timetable, delay_recovery, executor, **kwargs):
        """ Includes methods to monitor the schedule of a robot's allocated tasks
        """
        self.robot_id = robot_id
        self.timetable = timetable
        self.timetable.fetch()
        self.recovery_method = delay_recovery.method
        self.executor = executor
        self.api = kwargs.get("api")

        self.d_graph_update_received = False
        self.current_task = None
        self.task_progress = None

        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)
        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def configure(self, **kwargs):
        api = kwargs.get('api')
        if api:
            self.api = api

    def d_graph_update_cb(self, msg):
        payload = msg['payload']
        self.logger.critical("Received DGraph update")
        d_graph_update = DGraphUpdate.from_payload(payload)
        d_graph_update.update_timetable(self.timetable)
        self.logger.debug("STN update %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph update %s", self.timetable.dispatchable_graph)
        self.d_graph_update_received = True

    def assign_timepoint(self, assigned_time, task, node_type):
        is_consistent = True
        self.logger.debug("Assigning time %s to task %s timepoint %s", assigned_time, task.task_id, node_type)
        try:
            self.timetable.assign_timepoint(assigned_time, task.task_id, node_type)

        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s node_type %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, e.task_id, e.node_type)
            self.timetable.stn.assign_timepoint(e.assigned_time, e.task_id, e.node_type, force=True)
            is_consistent = False

        return is_consistent

    def update_current_task(self, task):
        self.current_task = task

    def run(self):
        if self.current_task and self.task_progress is None:
            self.initialize_task_progress()

        elif self.task_progress.action_status.status == ActionStatusConst.COMPLETED:
            self.complete_execution()

        elif not self.recovery_method.name.startswith("re-schedule") or \
                self.recovery_method.name.startswith("re-schedule") and self.d_graph_update_received:

            self.d_graph_update_received = False

            action = Action.get_action(self.task_progress.action_id)
            start_node, finish_node = action.get_node_names()
            r_start_time = self.timetable.stn.get_time(self.current_task.task_id, start_node)
            start_time = self.timetable.ztp + timedelta(seconds=r_start_time)
            self.update_task_progress(ActionStatusConst.ONGOING, start_time, start=True)
            self.executor.send_task_status(self.current_task, self.task_progress)

            finish_time = self.executor.execute(action, start_time)
            self.update_task_progress(ActionStatusConst.COMPLETED, finish_time, start=False)
            is_consistent = self.update_stn(self.current_task, action, self.task_progress.timestamp)
            self.executor.send_task_status(self.current_task, self.task_progress)

            self.recover(self.current_task, is_consistent)

            self.update_action_progress()

    def initialize_task_progress(self):
        # Get first action
        action = self.current_task.plan[0].actions[0]
        self.task_progress = TaskProgress(action.action_id, action.type)
        self.logger.debug("Starting execution of task %s", self.current_task.task_id)
        self.current_task.update_status(TaskStatusConst.ONGOING)
        self.current_task.update_progress(self.task_progress.action_id, self.task_progress.action_status.status)

    def update_task_progress(self, action_status, time_, start=True):
        kwargs = {}

        if start:
            kwargs.update(start_time=time_.to_datetime())
        else:
            kwargs.update(start_time=self.task_progress.timestamp.to_datetime(), finish_time=time_.to_datetime())

        self.task_progress.timestamp = time_
        self.task_progress.update_action_status(action_status)
        self.current_task.update_progress(self.task_progress.action_id, self.task_progress.action_status.status, **kwargs)

    def update_stn(self, task, action, timestamp):
        r_finish_time = timestamp.get_difference(self.timetable.ztp).total_seconds()
        start_node, finish_node = action.get_node_names()
        is_consistent = self.assign_timepoint(r_finish_time, task, finish_node)
        self.timetable.stn.execute_timepoint(task.task_id, start_node)
        self.timetable.stn.execute_timepoint(task.task_id, finish_node)
        start_node_idx, finish_node_idx = self.timetable.stn.get_edge_nodes_idx(task.task_id, start_node, finish_node)
        self.timetable.stn.execute_edge(start_node_idx, finish_node_idx)
        self.logger.debug("STN: \n %s",  self.timetable.stn)
        return is_consistent

    def update_action_progress(self):
        # Create task progress for new current action
        current_action = self.current_task.status.progress.current_action
        if current_action.action_id != self.task_progress.action_id:
            self.task_progress = TaskProgress(current_action.action_id, current_action.type)

    def complete_execution(self):
        self.logger.debug("Task %s is completing execution", self.current_task.task_id)
        task_schedule = {"start_time": self.current_task.start_time,
                         "finish_time": self.task_progress.timestamp.to_datetime()}
        self.current_task.update_schedule(task_schedule)
        self.current_task.update_status(TaskStatusConst.COMPLETED)
        self.executor.send_task_status(self.current_task, self.task_progress)
        self.current_task = None
        self.task_progress = None

    def recover(self, task, is_consistent):
        """ Applies a recovery method (preventive or corrective) if needed.
        A preventive recovery prevents delay of next_task. Applied BEFORE current task becomes inconsistent
        A corrective recovery prevents delay of next task. Applied AFTER current task becomes inconsistent

        task (Task) : current task
        is_consistent (boolean): True if the last assignment was consistent, false otherwise
        """

        if self.recovery_method.recover(self.timetable, task, is_consistent):
            if self.recovery_method.name == "re-allocate":
                next_task = self.timetable.get_next_task(task)
                self.re_allocate(next_task)

            elif self.recovery_method.name.startswith("re-schedule"):
                self.re_schedule(self.current_task)

            elif self.recovery_method.name == "abort":
                next_task = self.timetable.get_next_task(task)
                self.abort(next_task)

    def send_recover_msg(self, recover):
        msg = self.api.create_message(recover)
        self.api.publish(msg)

    def re_allocate(self, task):
        self.logger.debug("Trigger re-allocation of task %s", task.task_id)
        task.update_status(TaskStatusConst.UNALLOCATED)
        self.timetable.remove_task(task.task_id)
        recover = RecoverTask("re-allocate", task.task_id, self.robot_id)
        self.send_recover_msg(recover)

    def abort(self, task):
        self.logger.debug("Trigger abortion of task %s", task.task_id)
        task.update_status(TaskStatusConst.ABORTED)
        self.timetable.remove_task(task.task_id)
        recover = RecoverTask("abort", task.task_id, self.robot_id)
        self.send_recover_msg(recover)

    def re_schedule(self, task):
        self.logger.debug("Trigger rescheduling")
        recover = RecoverTask("re-schedule", task.task_id, self.robot_id)
        self.send_recover_msg(recover)
