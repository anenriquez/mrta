from mrs.db_interface import DBInterface


class ScheduleMonitor(object):
    def __init__(self, robot_common, schedule_monitor_config):
        self.common = robot_common
