from fleet_management.exceptions.config import InvalidConfig
from mrs.task_allocation import auctioneer
from mrs.task_execution import dispatcher
import logging


class MRTABuilder:
    def __init__(self):
        self._auctioneer = None
        self._dispatcher = None

    def __call__(self, **kwargs):
        plugins = dict()
        for plugin, config in kwargs.items():
            if plugin == 'auctioneer':
                self.auctioneer(**kwargs)
                plugins.update(auctioneer=self._auctioneer)
            if plugin == 'dispatcher':
                self.dispatcher(**kwargs)
                plugins.update(dispatcher=self._dispatcher)

        return plugins

    def auctioneer(self, **kwargs):
        if not self._auctioneer:
            try:
                self._auctioneer = auctioneer.configure(**kwargs)
            except InvalidConfig:
                raise InvalidConfig('MRTA plugin requires an auctioneer configuration')
        return self._auctioneer

    def dispatcher(self, **kwargs):
        if not self._dispatcher:
            try:
                self._dispatcher = dispatcher.configure(**kwargs)
            except InvalidConfig:
                raise InvalidConfig('MRTA plugin requires a dispatcher configuration')
        return self._dispatcher

    def get_component(self, name):
        if name == 'auctioneer':
            return self._auctioneer
        elif name == 'dispatcher':
            return self.dispatcher

    @classmethod
    def configure(cls, api, ccu_store, config_params):
        mrta_builder = cls()
        logging.info("Configuring MRTA...")
        mrta_config = config_params.get('plugins').get('mrta')
        if mrta_config is None:
            logging.debug("Found no mrta in the configuration file.")
            return None

        mrta_builder(api=api, ccu_store=ccu_store, **mrta_config)
        return mrta_builder
