from fleet_management.exceptions.config import InvalidConfig
from mrs.task_allocation import auctioneer
from mrs.task_execution import dispatcher
from mrs.task_allocation import bidder
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


class RobotBuilder:
    def __init__(self):
        self._bidder = None

    def __call__(self, **kwargs):
        components = dict()
        for component, config in kwargs.items():
            if component == 'bidder':
                bidder_config = kwargs.get('bidder')
                self.bidder(bidder_config, **kwargs)
                components.update(bidder=self._bidder)

        return components

    def bidder(self, bidder_config, **kwargs):
        if not self._bidder:
            try:
                self._bidder = bidder.configure(bidder_config, **kwargs)
            except InvalidConfig:
                raise InvalidConfig('Robot requires a bidder configuration')
            return self._bidder

    def get_component(self, name):
        if name == 'bidder':
            return self._bidder

    @classmethod
    def configure(cls, robot_id, api, robot_store, robot_config):
        robot_builder = cls()
        logging.info("Configuring Robot...")
        robot_components = robot_config.get('components')
        if robot_components is None:
            logging.debug("Found no robot components in the configuration file.")
            return None

        robot_builder(robot_id=robot_id, api=api, robot_store=robot_store, **robot_components)
        return robot_builder
