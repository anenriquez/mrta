
import logging
from datetime import timedelta

from mrs.task_execution.scheduler import Scheduler
from stn.stp import STP
from mrs.task_allocation.allocation_method import allocation_method_factory


class Dispatcher(object):

    def __init__(self, allocation_method, freeze_window, **kwargs):
        self.logger = logging.getLogger('mrs.dispatcher')
        self.api = None
        self.ccu_store = None

        stp_solver = allocation_method_factory.get_stp_solver(allocation_method)
        self.stp = STP(stp_solver)

        self.freeze_window = timedelta(minutes=freeze_window)
        self.re_allocate = kwargs.get('re_allocate', False)
        self.robot_ids = list()
        self.scheduler = Scheduler(self.stp)

        self.logger.debug("Dispatcher started")

    def configure(self, api, ccu_store):
        self.api = api
        self.ccu_store = ccu_store




