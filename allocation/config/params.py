from pyre_base.zyre_params import ZyreParams


class RopodParams(object):
    def __init__(self):
        self.id = ''


class ConfigParams(object):
    def __init__(self):
        self.ropods = list()
        self.bidding_rule = ''
        self.auction_time = 0
        self.type_temporal_network = ''
        self.execution_strategy = ''
        self.task_allocator_zyre_params = ZyreParams()
