import argparse
import logging.config
import time

from fmlib.models.actions import Action
from fmlib.models.robot import Robot as RobotModel
from mrs.allocation.bidder import Bidder
from mrs.config.configurator import Configurator
from mrs.db.models.task import Task
from mrs.execution.delay_recovery import DelayRecovery
from mrs.messages.remove_task import RemoveTask
from mrs.messages.task_progress import TaskProgress
from mrs.simulation.simulator import Simulator, SimulatorInterface
from mrs.timetable.timetable import Timetable
from planner.planner import Planner
from ropod.structs.task import TaskStatus as TaskStatusConst

_component_modules = {'simulator': Simulator,
                      'timetable': Timetable,
                      'bidder': Bidder,
                      'planner': Planner,
                      'delay_recovery': DelayRecovery}


class RobotProxy:
    def __init__(self, robot_id, api, robot_proxy_store, bidder, timetable, **kwargs):
        self.logger = logging.getLogger('mrs.robot.proxy%s' % robot_id)

        self.robot_id = robot_id
        self.api = api
        self.robot_proxy_store = robot_proxy_store
        self.bidder = bidder
        self.timetable = timetable
        self.robot_model = RobotModel.create_new(robot_id)
        self.simulator_interface = SimulatorInterface(kwargs.get('simulator'))

        self.api.register_callbacks(self)
        self.logger.info("Initialized RobotProxy %s", robot_id)

    def robot_pose_cb(self, msg):
        payload = msg.get("payload")
        self.logger.debug("Robot %s received pose", self.robot_id)
        self.robot_model.update_position(**payload.get("pose"))

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        if self.robot_id in task.assigned_robots:
            self.logger.debug("Received task %s", task.task_id)
            task.freeze()

    def task_progress_cb(self, msg):
        payload = msg['payload']
        progress = TaskProgress.from_payload(payload)
        if self.robot_id == progress.robot_id:
            self.logger.debug("Task progress received: %s", progress)
            task = Task.get_task(progress.task_id)
            action_progress = progress.action_progress

            if progress.status not in [TaskStatusConst.COMPLETED, TaskStatusConst.CANCELED, TaskStatusConst.ABORTED]:
                self._update_timetable(task, action_progress)
                self._update_task_schedule(task, action_progress)
                self._update_task_progress(task, action_progress)

    def remove_task_cb(self, msg):
        payload = msg['payload']
        remove_task = RemoveTask.from_payload(payload)
        task = Task.get_task(remove_task.task_id)
        self._remove_task(task, remove_task.status)

    def _update_timetable(self, task, action_progress):
        if action_progress.start_time and action_progress.finish_time:
            self.logger.debug("Updating timetable")
            action = Action.get_action(action_progress.action_id)
            start_node, finish_node = action.get_node_names()
            self.timetable.update_timetable(task.task_id, start_node, finish_node,
                                            action_progress.r_start_time, action_progress.r_finish_time)
            self.bidder.changed_timetable = True

            self.logger.debug("Updated stn: \n %s ", self.timetable.stn)
            self.logger.debug("Updated dispatchable graph: \n %s", self.timetable.dispatchable_graph)

    def _update_task_schedule(self, task, action_progress):
        first_action = task.plan[0].actions[0]
        last_action = task.plan[0].actions[-1]

        if action_progress.action_id == first_action.action_id and \
                action_progress.start_time and not task.start_time:
            self.logger.debug("Task %s start time %s", task.task_id, action_progress.start_time)
            task.update_start_time(action_progress.start_time)

        elif action_progress.action_id == last_action.action_id and \
                action_progress.finish_time and not task.finish_time:
            self.logger.debug("Task %s finish time %s", task.task_id, action_progress.finish_time)
            task.update_finish_time(action_progress.finish_time)

    def _update_task_progress(self, task, action_progress):
        self.logger.debug("Updating task progress of task %s", task.task_id)
        task.update_progress(action_progress.action_id, action_progress.status)

    def _remove_task(self, task, status):
        self.logger.critical("Deleting task %s from timetable and changing its status to %s", task.task_id, status)
        self.timetable.remove_task(task.task_id)
        self.bidder.changed_timetable = True
        task.update_status(status)
        self.logger.debug("STN: %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph: %s", self.timetable.dispatchable_graph)

    def run(self):
        try:
            self.api.start()
            while True:
                # time.sleep(0.1)
                pass
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.robot_id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    args = parser.parse_args()

    config = Configurator(args.file, component_modules=_component_modules)
    components = config.config_robot_proxy(args.robot_id)

    robot = RobotProxy(**components)
    robot.run()
