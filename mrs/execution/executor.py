import logging

import numpy as np
from ropod.structs.status import ActionStatus, TaskStatus as TaskStatusConst

from mrs.exceptions.execution import InconsistentAssignment
from mrs.messages.assignment_update import Assignment
from mrs.db.models.task import TimepointConstraint
from datetime import datetime
import time


class Executor:
    def __init__(self, robot_id, timetable, max_seed, **kwargs):
        self.robot_id = robot_id
        self.timetable = timetable

        random_seed = np.random.randint(max_seed)
        self.random_state = np.random.RandomState(random_seed)

        self.delay_n_standard_dev = kwargs.get('delay_n_standard_dev', 0)

        self.logger = logging.getLogger("mrs.executor.%s" % self.robot_id)
        self.logger.debug("Executor initialized %s", self.robot_id)

    def start_execution(self, task):
        self.logger.info("Start executing task %s", task.task_id)
        task.update_status(TaskStatusConst.ONGOING)
        action = task.plan[0].actions[0]
        task.update_progress(action.action_id, ActionStatus.ONGOING)
        self.timetable.stn.execute_timepoint(task.task_id, "start")

    def execute_action(self, task, action):
        self.logger.debug("Current action %s: ", action.type)
        constraint = task.get_inter_timepoint_constraint(action.estimated_duration.name)
        duration = constraint.sample_duration(self.random_state, self.delay_n_standard_dev)

        start_node, finish_node = action.get_node_names()
        prev_action_time = self.timetable.stn.get_time(task.task_id, start_node)
        r_assigned_time = prev_action_time + duration

        assigned_time = TimepointConstraint.absolute_time(self.timetable.zero_timepoint, r_assigned_time)
        assignment = self.assign_timepoint(r_assigned_time, task.task_id, finish_node)
        self.logger.info("Task: %s Action: %s Time: %s", task.task_id, action.type, assigned_time)

        # wait until assigned_time is present time
        # TODO: Refactor execution to be controlled by while in robot.py
        while datetime.now() < assigned_time:
            time.sleep(0.1)

        self.execute(task.task_id, start_node, finish_node)

        task.update_progress(action.action_id, ActionStatus.COMPLETED)
        return assignment

    def assign_timepoint(self, assigned_time, task_id, node_type):
        self.logger.debug("Assigning time %s to task %s timepoint %s", assigned_time, task_id, node_type)
        try:
            self.timetable.assign_timepoint(assigned_time, task_id, node_type)
            assignment = Assignment(task_id, assigned_time, node_type, is_consistent=True)

        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s node_type %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, e.task_id, e.node_type)
            self.timetable.stn.assign_timepoint(e.assigned_time, e.task_id, e.node_type, force=True)
            assignment = Assignment(task_id, assigned_time, node_type, is_consistent=False)

        self.logger.debug("STN with assigned value %s", self.timetable.stn)
        return assignment

    def execute(self, task_id, start_node, finish_node):
        self.logger.critical("Execute task %s node %s", task_id, finish_node)
        self.timetable.stn.execute_timepoint(task_id, finish_node)
        start_node_idx, finish_node_idx = self.timetable.stn.get_edge_nodes_idx(task_id, start_node, finish_node)
        self.timetable.stn.execute_edge(start_node_idx, finish_node_idx)
        self.logger.debug("STN with executed timepoint: %s",  self.timetable.stn)
