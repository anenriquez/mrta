import logging
from datetime import timedelta

import numpy as np
from fmlib.models.actions import Action
from fmlib.models.tasks import TaskStatus
from planner.planner import Planner
from pymodm.context_managers import switch_collection
from pymodm.errors import DoesNotExist
from ropod.structs.status import ActionStatus as ActionStatusConst, TaskStatus as TaskStatusConst
from stn.pstn.distempirical import norm_sample

from mrs.exceptions.execution import InconsistentAssignment
from mrs.messages.task_status import TaskStatus as TaskStatusMsg, TaskProgress


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
        self.task_progress = None

        self.logger = logging.getLogger("mrs.executor.%s" % self.robot_id)
        self.logger.debug("Executor initialized %s", self.robot_id)

    def send_task_status(self, task):
        try:
            task_status = task.status
        except DoesNotExist:
            with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
                task_status = TaskStatus.objects.get({"_id": task.task_id})

        task_status = TaskStatusMsg(task.task_id, self.robot_id, task_status.status, self.task_progress, task_status.delayed)

        self.logger.debug("Sending task status for task %s", task.task_id)
        msg = self.api.create_message(task_status)
        msg["header"]["timestamp"] = self.task_progress.timestamp.to_str()
        self.api.publish(msg)

    def start_execution(self, task):
        self.logger.info("Starting execution of task %s", task.task_id)
        # Get first action
        action = task.plan[0].actions[0]

        # Set current task and create task progress object
        self.current_task = task
        self.task_progress = TaskProgress(action.action_id, action.type)

        # Update task
        task.update_status(TaskStatusConst.ONGOING)
        task.update_progress(self.task_progress.action_id, self.task_progress.action_status.status)

    def execute(self):
        action = Action.get_action(self.task_progress.action_id)
        self.logger.debug("Current action %s: ", action)

        start_node, finish_node = action.get_node_names()
        r_start_time = self.timetable.stn.get_time(self.current_task.task_id, start_node)
        self.update_progress(ActionStatusConst.ONGOING, r_start_time, start=True)
        self.send_task_status(self.current_task)

        duration = self.get_action_duration(action)

        r_finish_time = r_start_time + duration
        self.update_progress(ActionStatusConst.COMPLETED, r_finish_time, start=False)

        self.execute_stn(self.current_task.task_id, start_node, finish_node)
        self.send_task_status(self.current_task)

    def update_action_progress(self):
        # Create task progress for new current action
        current_action = self.current_task.status.progress.current_action
        if current_action.action_id != self.task_progress.action_id:
            self.task_progress = TaskProgress(current_action.action_id, current_action.type)

    def get_action_duration(self, action):
        source = action.locations[0]
        destination = action.locations[-1]
        path = self.planner.get_path(source, destination)
        mean, variance = self.planner.get_estimated_duration(path)
        stdev = round(variance**0.5, 3)
        duration = round(norm_sample(mean, stdev, self.random_state))
        self.logger.debug("Time between %s and %s: %s", source, destination, duration)
        return duration

    def update_progress(self, action_status, r_time, start=True):
        time_ = self.timetable.ztp + timedelta(seconds=r_time)
        self.task_progress.timestamp = time_
        self.task_progress.update_action_status(action_status)
        kwargs = {}

        if start:
            kwargs.update(start_time=time_.to_datetime())
        else:
            kwargs.update(finish_time=time_.to_datetime())

        self.current_task.update_progress(self.task_progress.action_id, self.task_progress.action_status.status, **kwargs)

    def complete_execution(self):
        self.logger.debug("Completing execution of task %s", self.current_task.task_id)
        self.current_task.update_finish_time(self.task_progress.timestamp.to_datetime())
        self.current_task.update_status(TaskStatusConst.COMPLETED)
        self.send_task_status(self.current_task)
        self.current_task = None

    def assign_timepoint(self, assigned_time, task_id, node_type):
        self.logger.debug("Assigning time %s to task %s timepoint %s", assigned_time, task_id, node_type)
        try:
            self.timetable.assign_timepoint(assigned_time, task_id, node_type)

        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s node_type %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, e.task_id, e.node_type)
            self.timetable.stn.assign_timepoint(e.assigned_time, e.task_id, e.node_type, force=True)
            self.task_progress.is_consistent = False

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
        r_finish_time = self.task_progress.timestamp.get_difference(self.timetable.ztp).total_seconds()
        self.assign_timepoint(r_finish_time, self.current_task.task_id, finish_node)
        self.timetable.stn.execute_timepoint(task_id, start_node)
        self.timetable.stn.execute_timepoint(task_id, finish_node)
        start_node_idx, finish_node_idx = self.timetable.stn.get_edge_nodes_idx(task_id, start_node, finish_node)
        self.timetable.stn.execute_edge(start_node_idx, finish_node_idx)
        self.logger.debug("STN: \n %s",  self.timetable.stn)
