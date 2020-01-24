import logging

from stn.exceptions.stp import NoSTPSolution

from mrs.exceptions.allocation import InvalidAllocation
from mrs.timetable.timetable import Timetable


class TimetableManager(object):
    """
    Manages the timetable of all the robots in the fleet
    """
    def __init__(self, stp_solver, **kwargs):
        self.logger = logging.getLogger("mrs.timetable.manager")
        self.timetables = dict()
        self.stp_solver = stp_solver
        self.simulator = kwargs.get('simulator')

        self.logger.debug("TimetableManager started")

    @property
    def ztp(self):
        if self.timetables:
            any_timetable = next(iter(self.timetables.values()))
            return any_timetable.ztp
        else:
            self.logger.error("The zero timepoint has not been initialized")

    @ztp.setter
    def ztp(self, time_):
        for robot_id, timetable in self.timetables.items():
            timetable.update_zero_timepoint(time_)

    def get_timetable(self, robot_id):
        return self.timetables.get(robot_id)

    def register_robot(self, robot_id):
        self.logger.debug("Registering robot %s", robot_id)
        timetable = Timetable(robot_id, self.stp_solver, simulator=self.simulator)
        timetable.fetch()
        self.timetables[robot_id] = timetable
        timetable.store()

    def fetch_timetables(self):
        for robot_id, timetable in self.timetables.items():
            timetable.fetch()

    def update_timetable(self, robot_id, insertion_point, temporal_metric, task):
        timetable = self.timetables.get(robot_id)

        try:
            stn, dispatchable_graph = timetable.solve_stp(task, insertion_point)
            dispatchable_graph.temporal_metric = temporal_metric
            timetable.stn = stn
            timetable.dispatchable_graph = dispatchable_graph
            self.timetables.update({robot_id: timetable})

        except NoSTPSolution:
            self.logger.warning("The STN is inconsistent with task %s in insertion point %s", task.task_id, insertion_point)
            raise InvalidAllocation(task.task_id, robot_id, insertion_point)

        timetable.store()

        self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
        self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

