from mrs.task_allocation.auctioneer import Auctioneer
from mrs.task_execution.dispatcher import Dispatcher
from mrs.task_allocation.bidder import Bidder
import logging


class MRTAFactory:
    def __init__(self):
        self.logger = logging.getLogger('mrta.config.components')
        self._components = {}

    def register_component(self, component_name, component):
        self._components[component_name] = component

    def get_components(self, allocation_method, **kwargs):
        components = dict()

        for component_name, config in kwargs.items():
            self.logger.debug("Creating %s", component_name)
            component = self._components.get(component_name)

            if not component:
                raise ValueError(component_name)

            _instance = component(allocation_method=allocation_method,
                                  **config)
            components[component_name] = _instance
        return components


mrta_factory = MRTAFactory()
mrta_factory.register_component('auctioneer', Auctioneer)
mrta_factory.register_component('dispatcher', Dispatcher)
mrta_factory.register_component('bidder', Bidder)

