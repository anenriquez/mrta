import logging

from mrs.allocation.auctioneer import Auctioneer
from mrs.dispatching.dispatcher import Dispatcher
from mrs.timetable.manager import TimetableManager
from stn.stp import STP
from mrs.config.robot import RobotFactory


class MRTAFactory:

    """ Maps an allocation method to its stp_solver solver """
    allocation_methods = {'tessi': 'fpc',
                          'tessi-srea': 'srea',
                          'tessi-dsc': 'dsc'
                          }

    def __init__(self, allocation_method, **kwargs):
        """
            Registers and creates MRTA (multi-robot task allocation) components

            Args:

                allocation_method(str): name of the allocation method

        """

        self.logger = logging.getLogger('mrta.config.components')
        self.allocation_method = allocation_method

        self._components = {}

        self.stp_solver = self.get_stp_solver()

        self.timetable_manager = TimetableManager(self.stp_solver)

        self.register_component('auctioneer', Auctioneer)
        self.register_component('dispatcher', Dispatcher)
        self.register_component('robot', RobotFactory())

    def get_stp_solver(self):
        stp_solver_name = self.allocation_methods.get(self.allocation_method)
        if not stp_solver_name:
            self.logger.error("The given allocation method is not available")
            raise ValueError(self.allocation_method)

        return STP(stp_solver_name)

    def register_component(self, component_name, component):
        self._components[component_name] = component

    def __call__(self, **kwargs):
        components = dict()

        for component_name, configuration in kwargs.items():
            self.logger.debug("Creating %s", component_name)
            component = self._components.get(component_name)

            if component:
                _instance = component(allocation_method=self.allocation_method,
                                      stp_solver=self.stp_solver,
                                      timetable_manager=self.timetable_manager,
                                      **configuration)

                components[component_name] = _instance

        return components

