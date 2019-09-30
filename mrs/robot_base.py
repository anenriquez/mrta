from datetime import datetime

from mrs.structs.timetable import Timetable
from ropod.utils.timestamp import TimeStamp
from stn.stp import STP
from mrs.task_allocation.allocation_method import allocation_method_factory


class RobotBase(object):
    def __init__(self, robot_id, allocation_method, **kwargs):
        """ Includes robot base attributes and methods

        Args:

            robot_id (str): id of the robot, e.g. ropod_001
            allocation_method (str): name of the allocation method
            kwargs:
                api (API): object that provides middleware functionality
                robot_store (robot_store): interface to interact with the db

        """

        self.id = robot_id
        self.api = kwargs.get('api')
        self.robot_store = kwargs.get('robot_store')

        stp_solver = allocation_method_factory.get_stp_solver(allocation_method)
        self.stp = STP(stp_solver)

        self.timetable = Timetable(robot_id, self.stp)

        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        self.timetable.zero_timepoint = TimeStamp()
        self.timetable.zero_timepoint.timestamp = today_midnight

    def configure(self, **kwargs):
        api = kwargs.get('api')
        robot_store = kwargs.get('robot_store')
        if api:
            self.api = api
        if robot_store:
            self.robot_store = robot_store
