import logging

import numpy as np
from fmlib.models.actions import Action
from fmlib.models.tasks import TaskStatus
from planner.planner import Planner
from pymodm.context_managers import switch_collection
from pymodm.errors import DoesNotExist
from ropod.structs.status import ActionStatus, TaskStatus as TaskStatusConst
from stn.pstn.distempirical import norm_sample

from mrs.db.models.actions import ActionProgress
from mrs.db.models.task import TimepointConstraint
from mrs.exceptions.execution import InconsistentAssignment
from mrs.messages.task_progress import TaskProgress


class Executor:
    def __init__(self, robot_id, api, timetable, max_seed, map_name, **kwargs):
        self.robot_id = robot_id
        self.api = api
        self.timetable = timetable

        random_seed = np.random.randint(max_seed)
        self.random_state = np.random.RandomState(random_seed)

        # This is a virtual executor that uses a graph to get the task durations
        self.planner = Planner(map_name)

        self.current_task = None
        self.action_progress = None

        self.logger = logging.getLogger("mrs.executor.%s" % self.robot_id)
        self.logger.debug("Executor initialized %s", self.robot_id)

    def send_task_progress(self, task):
        try:
            task_status = task.status
        except DoesNotExist:
            with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
                task_status = TaskStatus.objects.get({"_id": task.task_id})

        task_progress = TaskProgress(task.task_id, task_status.status, self.robot_id, self.action_progress,
                                     task_status.delayed)
        self.logger.debug("Sending task progress: \n %s", task_progress)
        msg = self.api.create_message(task_progress)
        self.api.publish(msg)

    def start_execution(self, task):
        self.logger.info("Starting execution of task %s", task.task_id)
        # Get first action
        action = task.plan[0].actions[0]

        # Set current task and create action progress object
        self.current_task = task
        self.action_progress = ActionProgress(action.action_id)

        # Update task
        task.update_status(TaskStatusConst.ONGOING)
        task.update_progress(self.action_progress.action.action_id, self.action_progress.status)

    def execute(self):
        action = Action.get_action(self.action_progress.action.action_id)
        self.logger.debug("Current action %s: ", action)

        start_node, finish_node = action.get_node_names()
        r_start_time = self.timetable.stn.get_time(self.current_task.task_id, start_node)
        self.update_action(ActionStatus.ONGOING, r_start_time)
        self.send_task_progress(self.current_task)

        duration = self.get_action_duration(action)

        r_finish_time = r_start_time + duration
        self.update_action(ActionStatus.COMPLETED, r_finish_time)

        self.execute_stn(self.current_task.task_id, start_node, finish_node)
        self.send_task_progress(self.current_task)

    def update_action_progress(self):
        progress = self.current_task.status.progress
        # Create action progress for new current action
        if progress.current_action.action_id != self.action_progress.action.action_id:
            self.action_progress = ActionProgress(progress.current_action.action_id)

    def get_action_duration(self, action):
        source = action.locations[0]
        destination = action.locations[-1]
        path = self.planner.get_path(source, destination)
        mean, variance = self.planner.get_estimated_duration(path)
        stdev = round(variance**0.5, 3)
        duration = round(norm_sample(mean, stdev, self.random_state))
        self.logger.debug("Time between %s and %s: %s", source, destination, duration)
        return duration

    def update_action(self, action_status, r_time):
        abs_time = TimepointConstraint.absolute_time(self.timetable.zero_timepoint, r_time)
        self.action_progress.update(action_status, abs_time, r_time)
        kwargs = {}
        if self.action_progress.start_time:
            kwargs.update(start_time=self.action_progress.start_time)
        if self.action_progress.finish_time:
            kwargs.update(finish_time=self.action_progress.finish_time)

        self.current_task.update_progress(self.action_progress.action.action_id, self.action_progress.status, **kwargs)

    def complete_execution(self):
        self.logger.debug("Completing execution of task %s", self.current_task.task_id)
        self.current_task.update_finish_time(self.action_progress.finish_time)
        self.current_task.update_status(TaskStatusConst.COMPLETED)
        self.send_task_progress(self.current_task)
        self.current_task = None

    def assign_timepoint(self, assigned_time, task_id, node_type):
        self.logger.debug("Assigning time %s to task %s timepoint %s", assigned_time, task_id, node_type)
        try:
            self.timetable.assign_timepoint(assigned_time, task_id, node_type)

        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s node_type %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, e.task_id, e.node_type)
            self.timetable.stn.assign_timepoint(e.assigned_time, e.task_id, e.node_type, force=True)
            self.action_progress.is_consistent = False

        if self.task_is_delayed(assigned_time, node_type):
            self.logger.warning("Task %s is delayed", self.current_task.task_id)
            self.current_task.mark_as_delayed()

    def task_is_delayed(self, assigned_time, node_type):
        constraint = self.current_task.get_timepoint_constraint(node_type)
        if constraint:
            r_earliest_time, r_latest_time = constraint.relative_to_ztp(self.timetable.ztp)
            if assigned_time > r_latest_time:
                return True
        return False

    def execute_stn(self, task_id, start_node, finish_node):
        self.assign_timepoint(self.action_progress.r_finish_time, self.current_task.task_id, finish_node)
        self.timetable.stn.execute_timepoint(task_id, start_node)
        self.timetable.stn.execute_timepoint(task_id, finish_node)
        start_node_idx, finish_node_idx = self.timetable.stn.get_edge_nodes_idx(task_id, start_node, finish_node)
        self.timetable.stn.execute_edge(start_node_idx, finish_node_idx)
        self.logger.debug("STN: \n %s",  self.timetable.stn)
