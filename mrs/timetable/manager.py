import logging
from datetime import datetime

from mrs.timetable.timetable import Timetable
from ropod.utils.timestamp import TimeStamp

from stn.exceptions.stp import NoSTPSolution
from mrs.exceptions.allocation import InvalidAllocation


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

    def register_robot(self, robot_id):
        self.logger.debug("Registering robot %s", robot_id)
        self.robot_ids.append(robot_id)
        timetable = Timetable(robot_id, self.stp_solver)
        timetable.fetch()
        self.timetables[robot_id] = timetable

    def fetch_timetables(self):
        for robot_id, timetable in self.timetables.items():
            timetable.fetch()

    def update_timetable(self, robot_id, insertion_point, temporal_metric, task_lot):
        timetable = self.timetables.get(robot_id)
        timetable.fetch()
        timetable.zero_timepoint = self.zero_timepoint
        try:
            stn, dispatchable_graph = timetable.solve_stp(task_lot, insertion_point)
            dispatchable_graph.temporal_metric = temporal_metric
            timetable.stn = stn
            timetable.dispatchable_graph = dispatchable_graph
            self.timetables.update({robot_id: timetable})
        except NoSTPSolution:
            self.logger.warning("The STN is inconsistent with task %s in insertion point %s", task_lot.task.task_id, insertion_point)
            raise InvalidAllocation(task_lot.task.task_id, robot_id, insertion_point)

        timetable.store()

        self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
        self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

