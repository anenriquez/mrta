import logging

import numpy as np
from fmlib.models.tasks import TaskStatus
from pymodm.context_managers import switch_collection
from pymodm.errors import DoesNotExist
from ropod.structs.status import ActionStatus, TaskStatus as TaskStatusConst

from mrs.db.models.task import Task
from mrs.exceptions.execution import InconsistentSchedule, InconsistentAssignment
from mrs.exceptions.execution import MissingDispatchableGraph
from mrs.execution.delay_management import DelayManagement, Preventive, Corrective
from mrs.messages.assignment_update import AssignmentUpdate
from mrs.messages.task_status import TaskStatus as TaskStatusMessage, ReAllocate
from mrs.scheduling.monitor import ScheduleMonitor


class ExecutorInterface:
    def __init__(self, robot_id, stp_solver, allocation_method, max_seed, **kwargs):

        self.robot_id = robot_id
        self.delay_n_standard_dev = kwargs.get('delay_n_standard_dev', 0)

        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        self.tasks = list()
        self.archived_tasks = list()

        delay_management = kwargs.get('delay_management', {'reaction_type': None, 'reaction_name': None})
        self.delay_management = DelayManagement(**delay_management, allocation_method=allocation_method)

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

        prev_action_time = self.schedule_monitor.stn.get_time(task.task_id, start_node)
        assigned_time = prev_action_time + duration
        try:
            self.schedule_monitor.assign_timepoint(assigned_time, task.task_id, finish_node)
            assignment_is_consistent = True
        except InconsistentAssignment:
            assignment_is_consistent = False

        self.schedule_monitor.execute_timepoint(task.task_id, finish_node)
        self.schedule_monitor.execute_edge(task.task_id, start_node, finish_node)

        self.logger.info("Task: %s Action: %s Time: %s", task.task_id, action.type, assigned_time)
        self.manage_delay(task, assignment_is_consistent)

        task.update_progress(action.action_id, ActionStatus.COMPLETED)

    def start_execution(self, task):
        self.logger.info("Start executing task %s", task.task_id)
        task.update_status(TaskStatusConst.ONGOING)
        action = task.plan[0].actions[0]
        task.update_progress(action.action_id, ActionStatus.ONGOING)
        self.schedule_monitor.execute_timepoint(task.task_id, "start")

    def send_task_status(self, task):
        try:
            task_status = task.status
        except DoesNotExist:
            with switch_collection(Task, Task.Meta.archive_collection):
                with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
                    task_status = TaskStatus.objects.get({"_id": task.task_id})

        self.logger.debug("Send task status of task %s", task.task_id)
        task_status = TaskStatusMessage(task.task_id, self.robot_id, task_status.status, task_status.delayed)
        msg = self.api.create_message(task_status)
        self.api.publish(msg)

    def send_re_allocate_task(self, task):
        re_allocate_task = ReAllocate(task.task_id, self.robot_id)
        msg = self.api.create_message(re_allocate_task)
        self.api.publish(msg)

    def remove_task(self, task):
        self.logger.info("Deleting task %s", task.task_id)
        if task in self.tasks:
            self.tasks.remove(task)
            self.archived_tasks.append(task)
        self.schedule_monitor.remove_task(task.task_id)

    def re_allocate(self, task):
        self.logger.debug("Trigger re-allocation of task %s", task.task_id)
        task.update_status(TaskStatusConst.UNALLOCATED)
        self.send_re_allocate_task(task)
        self.remove_task(task)

    def manage_delay(self, task, assignment_is_consistent):
        """ React to a possible delay:
            - apply a reaction (preventive or corrective)
            - if no reaction is configured and the current task is inconsistent, abort the next task.

        A preventive reaction prevents delay of next_task. Applied BEFORE current task becomes inconsistent
        A corrective reaction prevents delay of next task. Applied AFTER current task becomes inconsistent

        task (Task) : current task
        next_task (Task): next to be executed
        consistent (boolean): whether or not the current task is consistent with its temporal constraints
        """

        if isinstance(self.delay_management.reaction, Preventive) or \
                isinstance(self.delay_management.reaction, Corrective) and not assignment_is_consistent:
            self.react_to_possible_delay(task)

        else:
            next_task = self.schedule_monitor.get_next_task(task)
            if next_task:
                next_task.update_status(TaskStatusConst.ABORTED)
                self.remove_task(task)
                self.send_task_status(task)

    def react_to_possible_delay(self, task):
        next_task = self.schedule_monitor.get_next_task(task)

        if next_task and self.delay_management.reaction.name == "re-allocate" and \
                self.schedule_monitor.is_next_task_late(task, next_task):
            task.mark_as_delayed()
            self.send_task_status(task)
            self.re_allocate(next_task)

        elif self.delay_management.reaction.name == "re-schedule":
            self.logger.info("Send AssignmentUpdate msg")
            assignment_update = AssignmentUpdate(self.robot_id, self.schedule_monitor.scheduler.assignments)
            self.schedule_monitor.scheduler.clean_assignments()
            msg = self.api.create_message(assignment_update)
            self.api.publish(msg)

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

            if task.status.status == TaskStatusConst.SCHEDULED and task.is_executable():
                self.start_execution(task)

            if task.status.status == TaskStatusConst.ONGOING:
                current_action = task.status.progress.current_action
                current_action_progress = task.status.progress.get_action(current_action.action_id)

                if (current_action_progress.status == ActionStatus.ONGOING) or\
                        (current_action_progress.status == ActionStatus.PLANNED and not
                            self.delay_management.reaction.name == "re-schedule") or \
                        (current_action_progress.status == ActionStatus.PLANNED and
                            self.delay_management.reaction.name == "re-schedule" and self.schedule_monitor.queue_update_received):
                    self.schedule_monitor.queue_update_received = False
                    task.update_progress(current_action.action_id, ActionStatus.ONGOING)
                    self.execute_action(task, current_action)
                elif current_action_progress.status == ActionStatus.COMPLETED:
                    task.update_status(TaskStatusConst.COMPLETED)
                    self.remove_task(task)
                    self.send_task_status(task)

