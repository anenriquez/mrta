import logging

from stn.stp import STP

from mrs.allocation.auctioneer import Auctioneer
from mrs.allocation.bidder import Bidder
from mrs.dispatching.dispatcher import Dispatcher
from mrs.execution.interface import ExecutorInterface
from mrs.timetable.manager import TimetableManager
from planner.planner import Planner


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

        self.register_component('allocation_method', allocation_method)
        self.register_component('stp_solver', self.get_stp_solver())
        self.register_component('timetable_manager', TimetableManager(self._components.get('stp_solver')))

        self.register_component('auctioneer', Auctioneer)
        self.register_component('dispatcher', Dispatcher)
        self.register_component('bidder', Bidder)
        self.register_component('executor_interface', ExecutorInterface)
        self.register_component('planner', Planner)

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
            self.logger.debug("Creating %s", component_name)
            component = self._components.get(component_name)

            if component and isinstance(configuration, dict):
                _component = component(**configuration, **self._components)
                self._components[component_name] = _component

        return self._components


