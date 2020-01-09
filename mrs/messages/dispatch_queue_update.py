from mrs.utils.as_dict import AsDictMixin


class DispatchQueueUpdate(AsDictMixin):
    def __init__(self, zero_timepoint, stn, dispatchable_graph, **kwargs):
        self.zero_timepoint = zero_timepoint
        self.stn = stn
        self.dispatchable_graph = dispatchable_graph

    @property
    def meta_model(self):
        return "dispatch-queue-update"
