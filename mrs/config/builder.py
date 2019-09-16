from fleet_management.exceptions.config import InvalidConfig


class MRTABuilder:
    def __init__(self, auctioneer_configure, dispatcher_configure):
        self._auctioneer = None
        self._dispatcher = None
        self._auctioneer_configure = auctioneer_configure
        self._dispatcher_configure = dispatcher_configure

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
                self._auctioneer = self._auctioneer_configure(**kwargs)
            except InvalidConfig:
                raise InvalidConfig('MRTA plugin requires an auctioneer configuration')
        return self._auctioneer

    def dispatcher(self, **kwargs):
        if not self._dispatcher:
            try:
                self._dispatcher = self._dispatcher_configure(**kwargs)
            except InvalidConfig:
                raise InvalidConfig('MRTA plugin requires a dispatcher configuration')
        return self._dispatcher
