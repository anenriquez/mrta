from pyre_base.zyre_params import ZyreParams


class RopodParams(object):
    def __init__(self):
        self.id = ''


class ConfigParams(object):
    def __init__(self):
        self.ropods = list()
        self.bidding_rule = ''
        self.auction_time = 0
        self.scheduling_method = ''
        self.task_allocator_zyre_params = ZyreParams()
