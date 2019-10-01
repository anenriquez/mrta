from mrs.task_allocation.auctioneer import Auctioneer
from mrs.task_execution.dispatcher import Dispatcher
from mrs.task_allocation.bidder import Bidder
import logging
from stn.stp import STP


class MRTAFactory:

    """ Maps an allocation method to its stp_solver solver """
    allocation_methods = {'tessi': 'fpc',
                          'tessi-srea': 'srea',
                          'tessi-dsc': 'dsc'
                          }

    def __init__(self, allocation_method):
        """
            Registers and creates MRTA (multi-robot task allocation) components

            Args:

                allocation_method(str): name of the allocation method

        """

        self.logger = logging.getLogger('mrta.config.components')
        self.allocation_method = allocation_method
        self._components = {}

        stp_solver_name = self.allocation_methods.get(allocation_method)
        if not stp_solver_name:
            self.logger.error("The given allocation method is not available")
            raise ValueError(allocation_method)

        self.stp_solver = STP(stp_solver_name)

        self.register_component('auctioneer', Auctioneer)
        self.register_component('dispatcher', Dispatcher)
        self.register_component('bidder', Bidder)

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
                                      **configuration)
                components[component_name] = _instance

        return components

