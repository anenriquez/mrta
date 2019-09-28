from mrs.task_allocation.auctioneer import Auctioneer
from mrs.task_execution.dispatcher import Dispatcher
from mrs.task_allocation.bidder import Bidder
import logging
from fmlib.config.params import ConfigParams as ConfigParamsBase


class MRTAFactory:
    def __init__(self, allocation_method):
        self.logger = logging.getLogger('mrta.config.components')
        self.allocation_method = allocation_method
        self._components = {}

    def register_component(self, component_name, component):
        self._components[component_name] = component

    def __call__(self, **kwargs):
        components = dict()

        for component_name, configuration in kwargs.items():
            self.logger.debug("Creating %s", component_name)
            component = self._components.get(component_name)

            if component:
                _instance = component(allocation_method=self.allocation_method,
                                      **configuration)
                components[component_name] = _instance

        return components


class ConfigParams(ConfigParamsBase):
    default_config_module = 'mrs.config.default'


_config = ConfigParams.default()
_allocation_method = _config.component('allocation_method', _config)

mrta_factory = MRTAFactory(_allocation_method)
mrta_factory.register_component('auctioneer', Auctioneer)
mrta_factory.register_component('dispatcher', Dispatcher)
mrta_factory.register_component('bidder', Bidder)

