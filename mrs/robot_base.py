from datetime import datetime

from mrs.structs.timetable import Timetable
from ropod.utils.timestamp import TimeStamp


class RobotBase(object):
    def __init__(self, robot_id, stp_solver, **kwargs):
        """ Includes robot base attributes and methods

        Args:

            robot_id (str): id of the robot, e.g. ropod_001
            stp_solver (STP): Simple Temporal Problem object
            kwargs:
                api (API): object that provides middleware functionality
                robot_store (robot_store): interface to interact with the db

        """

        self.robot_id = robot_id
        self.api = kwargs.get('api')
        self.robot_store = kwargs.get('robot_store')

        self.stp_solver = stp_solver
        self.timetable = self.get_timetable()

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

    def get_timetable(self):
        return Timetable.fetch(self.robot_id, self.stp_solver)
