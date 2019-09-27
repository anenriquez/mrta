from mrs.task_allocation.auctioneer import Auctioneer


class AuctioneerBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, **kwargs):
        if not self._instance:
            self._instance = Auctioneer(**kwargs)
        return self._instance


configure = AuctioneerBuilder()
