import argparse
import logging.config

from fmlib.models.robot import Robot as RobotModel
from fmlib.models.tasks import TransportationTask as Task
from ropod.structs.status import TaskStatus as TaskStatusConst

from mrs.allocation.bidder import Bidder
from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.simulation.simulator import Simulator
from mrs.timetable.monitor import TimetableMonitorProxy
from mrs.timetable.timetable import Timetable

_component_modules = {'simulator': Simulator,
                      'timetable': Timetable,
                      'timetable_monitor': TimetableMonitorProxy,
                      'bidder': Bidder,
                      }


class RobotProxy:
    def __init__(self, robot_id, api, robot_proxy_store, bidder, timetable_monitor, **kwargs):
        self.logger = logging.getLogger('mrs.robot.proxy%s' % robot_id)

        self.robot_id = robot_id
        self.api = api
        self.robot_proxy_store = robot_proxy_store
        self.bidder = bidder
        self.timetable_monitor = timetable_monitor
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
