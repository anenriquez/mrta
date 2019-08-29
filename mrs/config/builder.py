from fleet_management.exceptions.config import InvalidConfig
from mrs.task_allocation import auctioneer


class MRTABuilder:
    def __init__(self):
        self._auctioneer = None

    def __call__(self, **kwargs):
        plugins = dict()
        for plugin, config in kwargs.items():
            if plugin == 'auctioneer':
                self.auctioneer(**kwargs)
                plugins.update(auctioneer=self._auctioneer)

        return plugins

    def auctioneer(self, **kwargs):
        if not self._auctioneer:
            try:
                self._auctioneer = auctioneer.configure(**kwargs)
            except InvalidConfig:
                raise InvalidConfig('MRTA plugin requires an auctioneer configuration')
        return self._auctioneer
