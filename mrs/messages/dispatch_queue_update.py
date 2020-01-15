from mrs.utils.as_dict import AsDictMixin


class DispatchQueueUpdate(AsDictMixin):
    def __init__(self, zero_timepoint, stn, dispatchable_graph, **kwargs):
        self.zero_timepoint = zero_timepoint
        self.stn = stn
        self.dispatchable_graph = dispatchable_graph

    def update_timetable(self, timetable):
        stn_cls = timetable.stp.get_stn()
        timetable.zero_timepoint = self.zero_timepoint
        timetable.stn = stn_cls.from_dict(self.stn)
        timetable.dispatchable_graph = stn_cls.from_dict(self.dispatchable_graph)
        timetable.store()

    @property
    def meta_model(self):
        return "dispatch-queue-update"
