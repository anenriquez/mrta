import argparse
import logging.config

from fmlib.models.actions import Action
from fmlib.models.robot import Robot as RobotModel
from mrs.allocation.bidder import Bidder
from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.db.models.task import Task
from mrs.messages.recover_task import RecoverTask
from mrs.messages.remove_task import RemoveTask
from mrs.messages.task_progress import TaskProgress
from mrs.simulation.simulator import Simulator
from mrs.timetable.timetable import Timetable
from planner.planner import Planner
from ropod.structs.task import TaskStatus as TaskStatusConst
from stn.exceptions.stp import NoSTPSolution

_component_modules = {'simulator': Simulator,
                      'timetable': Timetable,
                      'bidder': Bidder,
                      'planner': Planner,
                      }


class RobotProxy:
    def __init__(self, robot_id, api, robot_proxy_store, bidder, timetable, **kwargs):
        self.logger = logging.getLogger('mrs.robot.proxy%s' % robot_id)

        self.robot_id = robot_id
        self.api = api
        self.robot_proxy_store = robot_proxy_store
        self.bidder = bidder
        self.timetable = timetable
        self.robot_model = RobotModel.create_new(robot_id)

        self.api.register_callbacks(self)
        self.logger.info("Initialized RobotProxy %s", robot_id)

    def robot_pose_cb(self, msg):
        payload = msg.get("payload")
        if payload.get("robotId") == self.robot_id:
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

    def recover_task_cb(self, msg):
        payload = msg['payload']
        recover = RecoverTask.from_payload(payload)
        if recover.robot_id == self.robot_id and recover.method == "re-schedule":
            self._re_compute_dispatchable_graph()

    def _update_timetable(self, task, action_progress):
        if action_progress.start_time and action_progress.finish_time:
            self.logger.debug("Updating timetable")
            action = Action.get_action(action_progress.action.action_id)
            start_node, finish_node = action.get_node_names()
            self.timetable.update_timetable(task.task_id, start_node, finish_node,
                                            action_progress.r_start_time, action_progress.r_finish_time)
            self.bidder.changed_timetable = True

            self.logger.debug("Updated stn: \n %s ", self.timetable.stn)
            self.logger.debug("Updated dispatchable graph: \n %s", self.timetable.dispatchable_graph)

    def _update_task_schedule(self, task, action_progress):
        first_action = task.plan[0].actions[0]
        last_action = task.plan[0].actions[-1]

        if action_progress.action.action_id == first_action.action_id and \
                action_progress.start_time and not task.start_time:
            self.logger.debug("Task %s start time %s", task.task_id, action_progress.start_time)
            task.update_start_time(action_progress.start_time)

        elif action_progress.action.action_id == last_action.action_id and \
                action_progress.finish_time and not task.finish_time:
            self.logger.debug("Task %s finish time %s", task.task_id, action_progress.finish_time)
            task.update_finish_time(action_progress.finish_time)

    def _update_task_progress(self, task, action_progress):
        self.logger.debug("Updating task progress of task %s", task.task_id)
        kwargs = {}
        if action_progress.start_time:
            kwargs.update(start_time=action_progress.start_time)
        if action_progress.finish_time:
            kwargs.update(finish_time=action_progress.finish_time)
        task.update_progress(action_progress.action.action_id, action_progress.status, **kwargs)

    def _remove_task(self, task, status):
        self.logger.critical("Deleting task %s from timetable and changing its status to %s", task.task_id, status)
        next_task = self.timetable.get_next_task(task)

        if status == TaskStatusConst.COMPLETED:
            if next_task:
                finish_current_task = self.timetable.stn.get_time(task.task_id, 'delivery', False)
                self.timetable.stn.assign_earliest_time(finish_current_task, next_task.task_id, 'start', force=True)
            self.update_robot_pose(task)
            self.timetable.remove_task(task.task_id)

        else:
            prev_task = self.timetable.get_previous_task(task)
            self.timetable.remove_task(task.task_id)
            if prev_task and next_task:
                self.update_pre_task_constraint(task, next_task)

        task.unfreeze()
        task.update_status(status)
        self.logger.debug("STN: %s", self.timetable.stn)
        self._re_compute_dispatchable_graph()

    def _re_compute_dispatchable_graph(self):
        self.logger.critical("Recomputing dispatchable graph of robot %s", self.timetable.robot_id)
        try:
            self.timetable.dispatchable_graph = self.timetable.compute_dispatchable_graph(self.timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", self.timetable.robot_id, self.timetable.dispatchable_graph)
            self.bidder.changed_timetable = True
        except NoSTPSolution:
            self.logger.warning("Temporal network is inconsistent")

    def update_robot_pose(self, task):
        x, y, theta = self.bidder.planner.get_pose(task.request.delivery_location)
        self.robot_model.update_position(x=x, y=y, theta=theta)

    def update_pre_task_constraint(self, task, next_task):
        self.logger.critical("Update pre_task constraint of task %s", next_task.task_id)
        position = self.timetable.get_task_position(next_task.task_id)
        prev_location = self.bidder.get_previous_location(position)
        travel_time = self.bidder.update_pre_task_constraint(next_task, prev_location)

        stn_task = self.timetable.get_stn_task(next_task.task_id)
        task.update_inter_timepoint_constraint(**travel_time.to_dict())
        stn_task.update_inter_timepoint_constraint(**travel_time.to_dict())
        self.timetable.add_stn_task(stn_task)
        self.timetable.update_task(stn_task)

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
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('--experiment', type=str, action='store', help='Experiment_name')
    parser.add_argument('--approach', type=str, action='store', help='Approach name')
    args = parser.parse_args()

    config_params = get_config_params(args.file, experiment=args.experiment, approach=args.approach)

    print("Experiment: ", config_params.get("experiment"))
    print("Approach: ", config_params.get("approach"))

    config = Configurator(config_params, component_modules=_component_modules)
    components = config.config_robot_proxy(args.robot_id)

    robot = RobotProxy(**components)
    robot.run()
