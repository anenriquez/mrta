
import logging
from datetime import timedelta

from mrs.task_execution.scheduler import Scheduler
from stn.stp import STP


class Dispatcher(object):

    def __init__(self, ccu_store, api, stp_solver, freeze_window, **kwargs):
        self.logger = logging.getLogger('mrs.dispatcher')

        self.api = api
        self.stp = STP(stp_solver)
        self.freeze_window = timedelta(minutes=freeze_window)
        self.re_allocate = kwargs.get('re_allocate', False)
        self.robot_ids = list()
        self.scheduler = Scheduler(self.stp)

        self.logger.debug("Dispatcher started")


class DispatcherBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, **kwargs):
        if not self._instance:
            self._instance = Dispatcher(**kwargs)
        return self._instance


configure = DispatcherBuilder()



