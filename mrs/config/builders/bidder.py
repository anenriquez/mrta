from mrs.task_allocation.bidder import Bidder


class BidderBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, bidder_config, **kwargs):
        if not self._instance:
            self._instance = Bidder(bidder_config, **kwargs)
        return self._instance


configure = BidderBuilder()
