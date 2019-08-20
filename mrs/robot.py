import argparse
import logging
import time
from importlib import import_module

from stn.stp import STP

from mrs.db_interface import DBInterface
from mrs.structs.timetable import Timetable
from mrs.task_allocation.bidder import Bidder
from mrs.task_execution.schedule_monitor import ScheduleMonitor


class RobotCommon(object):
    def __init__(self, robot_id, api, robot_store, stp_solver, task_type):

        self.id = robot_id
        self.api = api
        self.db_interface = DBInterface(robot_store)
        self.stp = STP(stp_solver)
        task_class_path = task_type.get('class', 'mrs.structs.task')
        self.task_cls = getattr(import_module(task_class_path), 'Task')

        self.timetable = Timetable.get_timetable(self.db_interface, self.id, self.stp)
        self.db_interface.update_timetable(self.timetable)


class Robot(object):

    def __init__(self, robot_common_config, bidder_config, **kwargs):

        self.common = RobotCommon(**robot_common_config)

        self.bidder = Bidder(self.common, bidder_config)

        schedule_monitor_config = kwargs.get("schedule_monitor_config")
        if schedule_monitor_config:
            self.schedule_monitor = ScheduleMonitor(self.common, schedule_monitor_config)

        self.logger = logging.getLogger('mrs.robot.%s' % self.common.id)
        self.logger.info("Robot %s initialized", self.common.id)

    def timetable_cb(self, msg):
        robot_id = msg['payload']['timetable']['robot_id']
        if robot_id == self.common.id:
            timetable_dict = msg['payload']['timetable']
            self.logger.debug("Robot %s received timetable msg", self.common.id)
            timetable = Timetable.from_dict(timetable_dict, self.common.stp)
            self.common.db_interface.update_timetable(timetable)

    def delete_task_cb(self, msg):
        task_dict = msg['payload']['task']
        task = self.common.task_cls.from_dict(task_dict)
        self.logger.debug("Deleting task %s ", task.id)
        self.common.db_interface.remove_task(task.id)

    def run(self):
        try:
            self.common.api.start()
            while True:
                time.sleep(0.5)

        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.common.id)
            self.common.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':

    from fleet_management.config.loader import Config

    config_file_path = '../config/config.yaml'
    config = Config(config_file_path, initialize=False)
    config.configure_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('robot_id', type=str, help='example: ropod_001')
    args = parser.parse_args()
    robot_id = args.robot_id

    robot = config.configure_robot_proxy(robot_id)

    robot.common.api.register_callbacks(robot)

    robot.run()


