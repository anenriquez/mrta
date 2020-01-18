import logging

from stn.stp import STP

from mrs.allocation.auctioneer import Auctioneer
from mrs.allocation.bidder import Bidder
from mrs.dispatching.dispatcher import Dispatcher
from mrs.execution.executor import Executor
from mrs.execution.schedule_monitor import ScheduleMonitor
from mrs.timetable.timetable_manager import TimetableManager

_component_modules = {'auctioneer': Auctioneer,
                      'dispatcher': Dispatcher,
                      'bidder': Bidder,
                      'executor': Executor,
                      'schedule_monitor': ScheduleMonitor}


class MRTAFactory:

    """ Maps an allocation method to its stp_solver solver """
    _allocation_methods = {'tessi': 'fpc',
                           'tessi-srea': 'srea',
                           'tessi-dsc': 'dsc',
                           }

    def __init__(self, allocation_method, **kwargs):
        """
            Registers and creates MRTA (multi-robot task allocation) components

            Args:

                allocation_method(str): name of the allocation method

        """

        self.logger = logging.getLogger('mrta.config.components')
        self._components = dict()
        self._component_modules = kwargs.get('component_modules', _component_modules)

        self.register_component('allocation_method', allocation_method)
        self.register_component('stp_solver', self.get_stp_solver())
        self.register_component('timetable_manager', TimetableManager(self._components.get('stp_solver')))

    def register_component(self, component_name, component):
        self._components[component_name] = component

    def get_stp_solver(self):
        allocation_method = self._components.get('allocation_method')
        stp_solver_name = self._allocation_methods.get(allocation_method)
        if not stp_solver_name:
            self.logger.error("The given allocation method is not available")
            raise ValueError(allocation_method)
        return STP(stp_solver_name)

    def __call__(self, **kwargs):
        for component_name, configuration in kwargs.items():
            if component_name in self._component_modules:
                self.logger.debug("Creating %s", component_name)
                component = self._component_modules.get(component_name)

                if component and isinstance(configuration, dict):
                    self.register_component(component_name, component)
                    _component = component(**configuration, **self._components)
                    self._components[component_name] = _component

        return self._components
