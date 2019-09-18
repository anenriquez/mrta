from fleet_management.exceptions.config import InvalidConfig
from mrs.config.builders import auctioneer
from mrs.config.builders import bidder
from mrs.config.builders import dispatcher


class MRTABuilder:
    def __init__(self):
        self._auctioneer = None
        self._dispatcher = None

    def __call__(self, **kwargs):
        components = dict()
        for component, config in kwargs.items():
            if component == 'auctioneer':
                self.auctioneer(**kwargs)
                components.update(auctioneer=self._auctioneer)
            if component == 'dispatcher':
                self.dispatcher(**kwargs)
                components.update(dispatcher=self._dispatcher)
            if component == 'bidder':
                bidder_config = kwargs.get('bidder')
                _bidder = self.bidder(bidder_config, **kwargs)
                components.update(bidder=_bidder)

        return components

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

    @staticmethod
    def bidder(bidder_config, **kwargs):
        try:
            _bidder = bidder.configure(bidder_config, **kwargs)
        except InvalidConfig:
            raise InvalidConfig('MRTA plugin requires a dispatcher configuration')
        return _bidder


configure = MRTABuilder()

