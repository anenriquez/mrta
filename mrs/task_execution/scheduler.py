import logging


class Scheduler(object):
    def __init__(self, stp):
        self.stp = stp
        self.n_tasks_sub_graphs = 2
        self.logger = logging.getLogger("mrs.scheduler")

