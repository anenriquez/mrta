from mrs.robot_base import RobotBase


class ScheduleMonitor(RobotBase):
    def __init__(self, robot_config, schedule_monitor_config):
        super().__init__(**robot_config)
