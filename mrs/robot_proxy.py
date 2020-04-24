import argparse
import logging.config

from fmlib.models.robot import Robot as RobotModel
from fmlib.models.tasks import TransportationTask as Task
from ropod.structs.status import TaskStatus as TaskStatusConst, ActionStatus as ActionStatusConst
from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution

from mrs.allocation.bidder import Bidder
from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.messages.remove_task import RemoveTaskFromSchedule
from mrs.messages.task_status import TaskStatus
from mrs.simulation.simulator import Simulator
from mrs.timetable.timetable import Timetable
from mrs.utils.time import relative_to_ztp

_component_modules = {'simulator': Simulator,
                      'timetable': Timetable,
                      'bidder': Bidder,
                      }


class RobotProxy:
    def __init__(self, robot_id, api, robot_proxy_store, bidder, timetable, **kwargs):
        self.logger = logging.getLogger('mrs.robot.proxy%s' % robot_id)

        self.robot_id = robot_id
        self.api = api
        self.robot_proxy_store = robot_proxy_store
        self.bidder = bidder
        self.timetable = timetable
        self.d_graph_watchdog = kwargs.get("d_graph_watchdog", False)
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
            task.update_status(TaskStatusConst.DISPATCHED)

    def task_status_cb(self, msg):
        payload = msg['payload']
        timestamp = TimeStamp.from_str(msg["header"]["timestamp"]).to_datetime()
        task_status = TaskStatus.from_payload(payload)

        if self.robot_id == task_status.robot_id:
            task = Task.get_task(task_status.task_id)
            self.logger.debug("Received task status %s for task %s", task_status.task_status, task.task_id)

            if task_status.task_status == TaskStatusConst.ONGOING:
                self._update_timetable(task, task_status.task_progress, timestamp)
                task.update_status(task_status.task_status)

    def remove_task_cb(self, msg):
        payload = msg['payload']
        remove_task = RemoveTaskFromSchedule.from_payload(payload)
        task = Task.get_task(remove_task.task_id)
        self._remove_task(task, remove_task.status)

    def _update_timetable(self, task, task_progress, timestamp):
        self.logger.debug("Updating timetable")

        r_assigned_time = relative_to_ztp(self.timetable.ztp, timestamp)
        first_action_id = task.plan[0].actions[0].action_id

        if task_progress.action_id == first_action_id and \
                task_progress.action_status.status == ActionStatusConst.ONGOING:
            node_id, node = self.timetable.stn.get_node_by_type(task.task_id, 'start')
            self._update_timepoint(task, r_assigned_time, node_id)
        else:
            # An action could be associated to two nodes, e.g., between pickup and delivery there is only one action
            nodes = self.timetable.stn.get_nodes_by_action(task_progress.action_id)

            for node_id, node in nodes:
                if (node.node_type == 'pickup' and
                    task_progress.action_status.status == ActionStatusConst.ONGOING) or \
                        (node.node_type == 'delivery' and
                         task_progress.action_status.status == ActionStatusConst.COMPLETED):
                    self._update_timepoint(task, r_assigned_time, node_id)

    def _update_timepoint(self, task, r_assigned_time, node_id):
        self.timetable.update_timepoint(r_assigned_time, node_id)

        nodes = self.timetable.stn.get_nodes_by_task(task.task_id)
        self._update_edge('start', 'pickup', nodes)
        self._update_edge('pickup', 'delivery', nodes)
        self.bidder.changed_timetable = True

        self.logger.debug("Updated stn: \n %s ", self.timetable.stn)
        self.logger.debug("Updated dispatchable graph: \n %s", self.timetable.dispatchable_graph)

        if self.d_graph_watchdog:
            self._re_compute_dispatchable_graph()

    def _update_edge(self, start_node, finish_node, nodes):
        node_ids = [node_id for node_id, node in nodes if (node.node_type == start_node and node.is_executed) or
                    (node.node_type == finish_node and node.is_executed)]
        if len(node_ids) == 2:
            self.timetable.execute_edge(node_ids[0], node_ids[1])

    def _remove_task(self, task, status):
        self.logger.debug("Deleting task %s from timetable and changing its status to %s", task.task_id, status)
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
                self.update_pre_task_constraint(next_task)

        task.update_status(status)
        self.logger.debug("STN: %s", self.timetable.stn)
        self.logger.debug("Dispatchable Graph: %s", self.timetable.dispatchable_graph)
        self._re_compute_dispatchable_graph()

    def _re_compute_dispatchable_graph(self):
        if self.timetable.stn.is_empty():
            self.logger.warning("Timetable of robot %s is empty", self.robot_id)
            return
        self.logger.debug("Recomputing dispatchable graph of robot %s", self.timetable.robot_id)
        try:
            self.timetable.dispatchable_graph = self.timetable.compute_dispatchable_graph(self.timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", self.timetable.robot_id, self.timetable.dispatchable_graph)
            self.bidder.changed_timetable = True
        except NoSTPSolution:
            self.logger.warning("Temporal network is inconsistent")

    def update_robot_pose(self, task):
        x, y, theta = self.bidder.planner.get_pose(task.request.delivery_location)
        self.robot_model.update_position(x=x, y=y, theta=theta)

    def update_pre_task_constraint(self, next_task):
        self.logger.debug("Update pre_task constraint of task %s", next_task.task_id)
        position = self.timetable.get_task_position(next_task.task_id)
        prev_location = self.bidder.get_previous_location(position)
        travel_duration = self.bidder.get_travel_duration(next_task, prev_location)

        stn_task = self.timetable.get_stn_task(next_task.task_id)
        stn_task.update_edge("travel_time", travel_duration.mean, travel_duration.variance)
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
    from planner.planner import Planner

    parser = argparse.ArgumentParser()
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('--experiment', type=str, action='store', help='Experiment_name')
    parser.add_argument('--approach', type=str, action='store', help='Approach name')
    args = parser.parse_args()

    config_params = get_config_params(args.file, experiment=args.experiment, approach=args.approach)
    config = Configurator(config_params, component_modules=_component_modules)
    components = config.config_robot_proxy(args.robot_id)

    for name, c in components.items():
        if hasattr(c, 'configure'):
            c.configure(planner=Planner(**config_params.get("planner")))

    robot = RobotProxy(**components, d_graph_watchdog=config_params.get("d_graph_watchdog"))
    robot.run()
