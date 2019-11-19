import logging


class Scheduler(object):
    def __init__(self, stp_solver, robot_id):
        self.stp_solver = stp_solver
        self.robot_id = robot_id
        self.logger = logging.getLogger("mrs.scheduler")
        self.is_scheduling = False

        self.logger.debug("Scheduler initialized %s", self.robot_id)
