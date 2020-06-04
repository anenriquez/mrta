import logging
from datetime import timedelta

import numpy as np
from fmlib.models.tasks import TransportationTask as Task
from fmlib.utils.messages import MessageFactory
from mrs.messages.task_status import TaskProgress
from mrs.messages.task_status import TaskStatus as TaskStatusMsg
from ropod.pyre_communicator.base_class import RopodPyre
from ropod.structs.status import ActionStatus as ActionStatusConst, TaskStatus as TaskStatusConst
from stn.pstn.distempirical import norm_sample


class Executor(RopodPyre):
    """ Mock-up executor that uses a graph to get the task durations and sends
    task-status messages

    """
    def __init__(self, robot_id, max_seed, **kwargs):
        self.robot_id = robot_id
        zyre_config = {'node_name': 'executor_' + robot_id,
                       'groups': ['ROPOD'],
                       'message_types': ['TASK', 'TASK-STATUS']}

        super().__init__(zyre_config, acknowledge=False)

        random_seed = np.random.randint(max_seed)
        self.random_state = np.random.RandomState(random_seed)
        self.task = None
        self.task_progress = None

        self._mf = MessageFactory()

        self.logger = logging.getLogger("mrs.executor.%s" % self.robot_id)
        self.logger.debug("Executor initialized %s", self.robot_id)
        self.start()

    def configure(self, **kwargs):
        for key, value in kwargs.items():
            self.logger.debug("Adding %s", key)
            self.__dict__[key] = value

    def receive_msg_cb(self, msg_content):
        msg = self.convert_zyre_msg_to_dict(msg_content)
        if msg is None:
            return
        msg_type = msg['header']['type']
        payload = msg['payload']

        if msg_type == 'TASK':
            task = Task.from_payload(payload)
            if self.robot_id in task.assigned_robots:
                self.logger.debug("Received task %s", task.task_id)
                self.task = task

    def run(self):
        if self.task:

            self.logger.debug("Starting execution of task %s", self.task.task_id)

            finish_time_last_action = None

            for i, action in enumerate(self.task.plan[0].actions):
                self.task_progress = TaskProgress(action.action_id, action.type)
                if i == 0:
                    finish_time_last_action = self.execute(action, self.task.start_time)
                elif i > 0:
                    finish_time_last_action = self.execute(action, finish_time_last_action)

            self.logger.debug("Completing execution of task %s", self.task.task_id)
            self.send_task_status(TaskStatusConst.COMPLETED)
            self.task = None
            self.task_progress = None

    def send_task_status(self, task_status):
        task_status = TaskStatusMsg(self.task.task_id, self.robot_id, task_status, self.task_progress)
        self.logger.debug("Sending task status for task %s", self.task.task_id)
        msg = self._mf.create_message(task_status)
        msg["header"]["timestamp"] = self.task_progress.timestamp.isoformat()
        self.whisper(msg, peer=self.robot_id)

    def execute(self, action, start_time):
        self.logger.debug("Executing action %s: %s ", action.action_id, action.type)

        self.logger.debug("action start time: %s", start_time)
        self.update_task_progress(ActionStatusConst.ONGOING, start_time)
        self.send_task_status(TaskStatusConst.ONGOING)

        duration = self.get_action_duration(action)
        finish_time = start_time + timedelta(seconds=duration)
        self.update_task_progress(ActionStatusConst.COMPLETED, finish_time)
        self.send_task_status(TaskStatusConst.ONGOING)

        self.logger.debug("action finish time: %s", finish_time)
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

    def update_task_progress(self, action_status, time_):
        self.task_progress.timestamp = time_
        self.task_progress.update_action_status(action_status)
