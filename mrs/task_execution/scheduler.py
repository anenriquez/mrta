import logging


class Scheduler(object):
    def __init__(self, stp_solver):
        self.stp_solver = stp_solver
        self.n_tasks_sub_graphs = 2
        self.logger = logging.getLogger("mrs.scheduler")

