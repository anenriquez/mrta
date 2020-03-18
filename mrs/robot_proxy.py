import argparse
import logging.config

from fmlib.models.actions import Action
from fmlib.models.robot import Robot as RobotModel
from planner.planner import Planner
from ropod.structs.status import TaskStatus as TaskStatusConst, ActionStatus as ActionStatusConst
from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution

from mrs.allocation.bidder import Bidder
from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.db.models.task import Task
from mrs.messages.recover_task import RecoverTask
from mrs.messages.remove_task import RemoveTask
from mrs.messages.task_status import TaskStatus
from mrs.simulation.simulator import Simulator
from mrs.timetable.timetable import Timetable

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

    def task_status_cb(self, msg):
        payload = msg['payload']
        timestamp = TimeStamp.from_str(msg["header"]["timestamp"])
        task_status = TaskStatus.from_payload(payload)

        if self.robot_id == task_status.robot_id and task_status.task_status == TaskStatusConst.ONGOING:
            self.logger.debug("Received task status message for task %s", task_status.task_id)

            task = Task.get_task(task_status.task_id)
            if not task.status.progress:
                task.update_progress(task_status.task_progress.action_id,
                                     task_status.task_progress.action_status.status)
            action_progress = task.status.progress.get_action(task_status.task_progress.action_id)

            self._update_timetable(task, task_status, action_progress, timestamp)
            self._update_task_schedule(task, task_status.task_progress, action_progress, timestamp)
            self._update_task_progress(task, task_status.task_progress, action_progress, timestamp)
            task.update_status(task_status.task_status)

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

    def _update_timetable(self, task, task_status, action_progress, timestamp):
        self.logger.debug("Updating timetable")

        # Get relative time (referenced to the ztp)
        assigned_time = timestamp.get_difference(self.timetable.ztp).total_seconds()

        action = Action.get_action(task_status.task_progress.action_id)
        start_node, finish_node = action.get_node_names()

        if task_status.task_progress.action_status.status == ActionStatusConst.ONGOING and\
                action_progress.start_time is None:
            self.timetable.update_timetable(assigned_time, task.task_id, start_node)

        elif task_status.task_progress.action_status.status == ActionStatusConst.COMPLETED and\
                action_progress.finish_time is None:
            self.timetable.update_timetable(assigned_time, task.task_id, finish_node)
            self.timetable.execute_edge(task.task_id, start_node, finish_node)

        self.bidder.changed_timetable = True
        self.logger.debug("Updated stn: \n %s ", self.timetable.stn)
        self.logger.debug("Updated dispatchable graph: \n %s", self.timetable.dispatchable_graph)

    def _update_task_schedule(self, task, task_progress, action_progress, timestamp):
        first_action = task.plan[0].actions[0]
        last_action = task.plan[0].actions[-1]

        if task_progress.action_id == first_action.action_id and action_progress.start_time is None:
            self.logger.debug("Task %s start time %s", task.task_id, timestamp)
            task.update_start_time(timestamp.to_datetime())

        elif task_progress.action_id == last_action.action_id and action_progress.finish_time is None:
            self.logger.debug("Task %s finish time %s", task.task_id, timestamp)
            task.update_finish_time(timestamp.to_datetime())

    def _update_task_progress(self, task, task_progress, action_progress, timestamp):
        self.logger.debug("Updating task progress of task %s", task.task_id)

        kwargs = {}
        if task_progress.action_status.status == ActionStatusConst.ONGOING and action_progress.start_time is None:
            kwargs.update(start_time=timestamp.to_datetime())
        elif task_progress.action_status.status == ActionStatusConst.COMPLETED and action_progress.finish_time is None:
            kwargs.update(start_time=action_progress.start_time, finish_time=timestamp.to_datetime())

        task.update_progress(task_progress.action_id, task_progress.action_status.status, **kwargs)

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
