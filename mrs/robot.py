import argparse
import logging
import time

from mrs.robot_base import RobotBase
from mrs.structs.timetable import Timetable
from mrs.task_allocation.bidder import Bidder
from mrs.task_execution.schedule_monitor import ScheduleMonitor


class Robot(RobotBase):
    def __init__(self, robot_config, bidder_config, **kwargs):
        super().__init__(**robot_config)

        self.bidder = Bidder(robot_config, bidder_config)

        schedule_monitor_config = kwargs.get("schedule_monitor_config")
        if schedule_monitor_config:
            self.schedule_monitor = ScheduleMonitor(robot_config, schedule_monitor_config)

        self.logger = logging.getLogger('mrs.robot.%s' % self.id)
        self.logger.info("Robot %s initialized", self.id)

    def run(self):
        try:
            self.api.start()
            while True:
                time.sleep(0.5)

        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':

    from fleet_management.config.loader import Configurator

    config_file_path = '../config/config.yaml'
    config = Configurator(config_file_path, initialize=False)
    config.configure_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('robot_id', type=str, help='example: ropod_001')
    args = parser.parse_args()
    robot_id = args.robot_id

    robot = config.configure_robot_proxy(robot_id)

    robot.api.register_callbacks(robot)

    robot.run()


