import logging

import numpy as np
from mrs.db.models.task import Task
from mrs.exceptions.execution import InconsistentSchedule, InconsistentAssignment
from mrs.exceptions.execution import MissingDispatchableGraph
from mrs.execution.corrective_measure import CorrectiveMeasure
from mrs.messages.task_progress import TaskProgress
from mrs.scheduling.monitor import ScheduleMonitor
from ropod.structs.status import ActionStatus, TaskStatus as TaskStatusConst


class ExecutorInterface:
    def __init__(self, robot_id, stp_solver, allocation_method, max_seed, **kwargs):

        self.robot_id = robot_id
        self.delay_n_standard_dev = kwargs.get('delay_n_standard_dev', 0)

        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        self.tasks = list()
        self.archived_tasks = list()
        self.task_to_archive = None

        corrective_measure_name = kwargs.get('corrective_measure')
        if corrective_measure_name:
            self.corrective_measure = CorrectiveMeasure(corrective_measure_name, allocation_method)
        else:
            self.corrective_measure = None

        time_resolution = kwargs.get('time_resolution', 0.5)
        self.schedule_monitor = ScheduleMonitor(robot_id, stp_solver, time_resolution)

        random_seed = np.random.randint(max_seed)
        self.random_state = np.random.RandomState(random_seed)

        self.logger = logging.getLogger("mrs.executor.interface.%s" % self.robot_id)
        self.logger.debug("Executor interface initialized %s", self.robot_id)

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        self.logger.critical("Received task %s", task.task_id)
        if self.robot_id in task.assigned_robots:
            task.update_status(TaskStatusConst.DISPATCHED)
            self.tasks.append(task)
            Task.freeze_task(task.task_id)

    def execute_action(self, task, action):
        self.logger.info("Executing action %s", action.type)
        constraint = task.get_inter_timepoint_constraint(action.estimated_duration.name)
        duration = constraint.sample_duration(self.random_state, self.delay_n_standard_dev)

        start_node, finish_node = action.get_node_names()

        prev_action_time = self.schedule_monitor.dispatchable_graph.get_time(task.task_id, start_node)
        action_time = prev_action_time + duration
        consistent = True
        try:
            self.schedule_monitor.assign_timepoint(action_time, task.task_id, finish_node)
        except InconsistentAssignment:
            consistent = False

        self.logger.info("Task: %s Action: %s Time: %s", task.task_id, action.type, action_time)

        next_task = self.schedule_monitor.get_next_task(task)
        if next_task:
            self.apply_corrective_measure(task, next_task, consistent)

        task.status.update_progress(action.action_id, ActionStatus.COMPLETED)

    def execute_task(self, task):
        self.logger.info("Executing task %s", task.task_id)
        task.update_status(TaskStatusConst.ONGOING)
        action = task.plan[0].actions[0]
        task.status.update_progress(action.action_id, ActionStatus.ONGOING)

        for action_progress in task.status.progress.actions:
            task.status.update_progress(action_progress.action.action_id, ActionStatus.ONGOING)
            self.execute_action(task, action_progress.action)

        task.update_status(TaskStatusConst.COMPLETED)
        self.send_task_progress(task, TaskStatusConst.COMPLETED)
        self.remove_task(task)

    def send_task_progress(self, task, status, re_allocate_next=False):
        self.logger.debug("Send task progress task %s", task.task_id)
        task_progress = TaskProgress(task.task_id, self.robot_id, status, re_allocate_next)
        task_progress_msg = self.api.create_message(task_progress)
        self.api.publish(task_progress_msg)

    def remove_task(self, task):
        self.logger.info("Deleting task %s", task.task_id)
        if task in self.tasks:
            self.tasks.remove(task)
            self.archived_tasks.append(task)
        self.schedule_monitor.remove_task(task.task_id)

    def re_allocate(self, task):
        self.logger.debug("Trigger re-allocation of task %s", task.task_id)
        task.update_status(TaskStatusConst.UNALLOCATED)

    def apply_corrective_measure(self, task, next_task, consistent):

        if not consistent and self.corrective_measure is None:
            next_task.update_status(TaskStatusConst.ABORTED)
            self.remove_task(task)

        elif (not consistent and self.corrective_measure.name == 'post-failure-re-allocate') or \
                (self.corrective_measure.name == 'pre-failure-re-allocate') and \
                self.schedule_monitor.is_next_task_late(task, next_task):
            task.status.delayed = True
            task.save()
            self.re_allocate(next_task)
            self.remove_task(next_task)
            self.send_task_progress(task, task.status.status, re_allocate_next=True)

        elif consistent and self.corrective_measure == 're-schedule':
            # Re-compute dispatchable graph
            pass

        elif not consistent and self.corrective_measure == 're-schedule':
            # Re-compute dispatchable graph and re-allocate next task
            pass

    def run(self):
        for task in self.tasks:
            if task.status.status == TaskStatusConst.DISPATCHED:
                try:
                    scheduled_task = self.schedule_monitor.schedule(task)
                    scheduled_task.update_status(TaskStatusConst.SCHEDULED)
                except MissingDispatchableGraph:
                    # TODO: Request DispatchQueueUpdate
                    pass
                except InconsistentSchedule:
                    self.re_allocate(task)
                    self.send_task_progress(task, task.status.status)
                    self.remove_task(task)

            if task.status.status == TaskStatusConst.SCHEDULED and task.is_executable():
                self.execute_task(task)
