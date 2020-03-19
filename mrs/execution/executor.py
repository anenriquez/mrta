import logging
from datetime import timedelta

import numpy as np
from fmlib.models.tasks import TaskStatus
from pymodm.context_managers import switch_collection
from pymodm.errors import DoesNotExist
from stn.pstn.distempirical import norm_sample

from mrs.messages.task_status import TaskStatus as TaskStatusMsg


class Executor:
    def __init__(self, robot_id, api, max_seed, map_name, **kwargs):
        self.robot_id = robot_id
        self.api = api

        random_seed = np.random.randint(max_seed)
        self.random_state = np.random.RandomState(random_seed)

        # This is a virtual executor that uses a graph to get the task durations

        self.logger = logging.getLogger("mrs.executor.%s" % self.robot_id)
        self.logger.debug("Executor initialized %s", self.robot_id)

    def configure(self, **kwargs):
        for key, value in kwargs.items():
            self.logger.debug("Adding %s", key)
            self.__dict__[key] = value

    def send_task_status(self, task, task_progress):
        try:
            task_status = task.status
        except DoesNotExist:
            with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
                task_status = TaskStatus.objects.get({"_id": task.task_id})

        task_status = TaskStatusMsg(task.task_id, self.robot_id, task_status.status, task_progress, task_status.delayed)

        self.logger.debug("Sending task status for task %s", task.task_id)
        msg = self.api.create_message(task_status)
        msg["header"]["timestamp"] = task_progress.timestamp.to_str()
        self.api.publish(msg)

    def execute(self, action, start_time):
        self.logger.debug("Current action %s: %s ", action.action_id, action.type)
        self.logger.debug("Start time: %s", start_time)
        duration = self.get_action_duration(action)
        finish_time = start_time + timedelta(seconds=duration)
        self.logger.debug("Finish time: %s", finish_time)
        return finish_time

    def get_action_duration(self, action):
        source = action.locations[0]
        destination = action.locations[-1]
        try:
            path = self.planner.get_path(source, destination)
            mean, variance = self.planner.get_estimated_duration(path)
            stdev = round(variance**0.5, 3)
            duration = round(norm_sample(mean, stdev, self.random_state))
        except AttributeError:
            self.logger.warning("No planner configured")
            duration = 1.0

        self.logger.debug("Time between %s and %s: %s", source, destination, duration)
        return duration
