from mrs.task_allocation.auctioneer import Auctioneer
from mrs.task_execution.dispatcher import Dispatcher
from mrs.task_allocation.bidder import Bidder
import logging
from fmlib.config.params import ConfigParams as ConfigParamsBase
from stn.stp import STP


class MRTAFactory:

    """ Maps an allocation method to its stp_solver solver """
    allocation_methods = {'tessi': 'fpc',
                          'tessi-srea': 'srea',
                          'tessi-dsc': 'dsc'
                          }

    def __init__(self, **kwargs):
        """
            Registers and creates MRTA (multi-robot task allocation) components

            Args:

                allocation_method(str): name of the allocation method

        """

        self.logger = logging.getLogger('mrta.config.components')
        self._components = {}

        allocation_method = kwargs.get('allocation_method')
        if allocation_method:
            stp_solver_name = self.allocation_methods.get(allocation_method)
            self.stp_solver = STP(stp_solver_name)

    def configure(self, **kwargs):
        allocation_method = kwargs.get('allocation_method')
        if allocation_method:
            stp_solver_name = self.allocation_methods.get(allocation_method)
            self.stp_solver = STP(stp_solver_name)

    def register_component(self, component_name, component):
        self._components[component_name] = component

    def __call__(self, **kwargs):
        components = dict()

        for component_name, configuration in kwargs.items():
            self.logger.debug("Creating %s", component_name)
            print("Creating: ", component_name)
            component = self._components.get(component_name)

            if component:
                _instance = component(stp_solver=self.stp_solver,
                                      **configuration)
                components[component_name] = _instance

        return components


class ConfigParams(ConfigParamsBase):
    default_config_module = 'mrs.config.default'


_config = ConfigParams.default()
_allocation_method = _config.component('allocation_method', _config)

mrta_factory = MRTAFactory(allocation_method=_allocation_method)
mrta_factory.register_component('auctioneer', Auctioneer)
mrta_factory.register_component('dispatcher', Dispatcher)
mrta_factory.register_component('bidder', Bidder)

