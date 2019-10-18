import logging
from datetime import datetime

from mrs.timetable.timetable import Timetable
from ropod.utils.timestamp import TimeStamp


class TimetableManager(object):
    """
    Manages the timetable of all the robots in the fleet
    """
    def __init__(self, stp_solver):
        self.logger = logging.getLogger("mrs.timetable.manager")
        self.robot_ids = list()
        self.timetables = dict()
        self.stp_solver = stp_solver
        self.zero_timepoint = self.initialize_zero_timepoint()

        self.logger.debug("TimetableManager started")

    @staticmethod
    def initialize_zero_timepoint():
        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        zero_timepoint = TimeStamp()
        zero_timepoint.timestamp = today_midnight
        return zero_timepoint

    def update_zero_timepoint(self):
        pass

    def register_fleet(self, fleet):
        for robot_id in fleet:
            self.robot_ids.append(robot_id)
            self.fetch_timetable(robot_id)

    def fetch_timetables(self):
        for robot_id in self.robot_ids:
            self.fetch_timetable(robot_id)

    def fetch_timetable(self, robot_id):
        timetable = Timetable.fetch(robot_id, self.stp_solver)
        self.timetables[robot_id] = timetable

    def update_timetable(self, robot_id, position, temporal_metric, task_lot):
        self.fetch_timetable(robot_id)
        timetable = self.timetables.get(robot_id)
        timetable.update(self.zero_timepoint, task_lot, position, temporal_metric)
        self.timetables.update({robot_id: timetable})
        timetable.store()

        self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
        self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

