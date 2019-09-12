from datetime import datetime
from importlib import import_module

from ropod.utils.timestamp import TimeStamp
from stn.stp import STP
from mrs.structs.timetable import Timetable

from mrs.db_interface import DBInterface


class RobotBase(object):
    def __init__(self, robot_id, api, robot_store, stp_solver, task_type):

        self.id = robot_id
        self.api = api
        # self.db_interface = DBInterface(robot_store)
        self.stp = STP(stp_solver)

        self.timetable = Timetable(robot_id, self.stp)

        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        self.timetable.zero_timepoint = TimeStamp()
        self.timetable.zero_timepoint.timestamp = today_midnight

