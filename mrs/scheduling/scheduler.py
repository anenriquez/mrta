import logging


class Scheduler(object):
    def __init__(self, stp_solver, robot_id):
        self.robot_id = robot_id
        self.stp_solver = stp_solver
        self.n_tasks_sub_graphs = 2
        self.logger = logging.getLogger("mrs.scheduler")

        self.logger.debug("Scheduler initialized %s", self.robot_id)

