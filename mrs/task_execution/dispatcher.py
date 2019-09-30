
import logging
from datetime import timedelta

from mrs.task_execution.scheduler import Scheduler
from stn.stp import STP
from mrs.task_allocation.allocation_method import allocation_method_factory


class Dispatcher(object):

    def __init__(self, allocation_method, freeze_window, **kwargs):
        self.logger = logging.getLogger('mrs.dispatcher')
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        stp_solver = allocation_method_factory.get_stp_solver(allocation_method)
        self.stp = STP(stp_solver)

        self.freeze_window = timedelta(minutes=freeze_window)
        self.re_allocate = kwargs.get('re_allocate', False)
        self.robot_ids = list()
        self.scheduler = Scheduler(self.stp)

        self.logger.debug("Dispatcher started")

    def configure(self, **kwargs):
        api = kwargs.get('api')
        ccu_store = kwargs.get('ccu_store')
        if api:
            self.api = api
        if ccu_store:
            self.ccu_store = ccu_store




