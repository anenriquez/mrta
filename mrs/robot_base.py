from datetime import datetime

from mrs.structs.timetable import Timetable
from ropod.utils.timestamp import TimeStamp
from stn.stp import STP
from mrs.task_allocation.allocation_method import allocation_method_factory


class RobotBase(object):
    def __init__(self, robot_id, allocation_method, **_):

        self.id = robot_id
        self.api = None
        self.robot_store = None

        stp_solver = allocation_method_factory.get_stp_solver(allocation_method)
        self.stp = STP(stp_solver)

        self.timetable = Timetable(robot_id, self.stp)

        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        self.timetable.zero_timepoint = TimeStamp()
        self.timetable.zero_timepoint.timestamp = today_midnight

    def configure(self, **kwargs):
        self.api = kwargs.get('api')
        self.robot_store = kwargs.get('robot_store')

