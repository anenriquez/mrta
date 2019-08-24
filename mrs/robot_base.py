from datetime import datetime
from importlib import import_module

from ropod.utils.timestamp import TimeStamp
from stn.stp import STP

from mrs.db_interface import DBInterface
from mrs.structs.timetable import Timetable


class RobotBase(object):
    def __init__(self, robot_id, api, robot_store, stp_solver, task_type):

        self.id = robot_id
        self.api = api
        self.db_interface = DBInterface(robot_store)
        self.stp = STP(stp_solver)
        task_class_path = task_type.get('class', 'mrs.structs.task')
        self.task_cls = getattr(import_module(task_class_path), 'Task')

        self.timetable = Timetable.get_timetable(self.db_interface, self.id, self.stp)
        self.db_interface.update_timetable(self.timetable)

        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        self.ztp = TimeStamp()
        self.ztp.timestamp = today_midnight

