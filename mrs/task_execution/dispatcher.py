
import logging
from datetime import timedelta

from mrs.task_execution.scheduler import Scheduler


class Dispatcher(object):

    def __init__(self, stp_solver, freeze_window, **kwargs):
        self.logger = logging.getLogger('mrs.dispatcher')
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        self.stp_solver = stp_solver

        self.freeze_window = timedelta(minutes=freeze_window)
        self.re_allocate = kwargs.get('re_allocate', False)
        self.robot_ids = list()
        self.scheduler = Scheduler(self.stp_solver)

        self.logger.debug("Dispatcher started")

    def configure(self, **kwargs):
        api = kwargs.get('api')
        ccu_store = kwargs.get('ccu_store')
        if api:
            self.api = api
        if ccu_store:
            self.ccu_store = ccu_store




