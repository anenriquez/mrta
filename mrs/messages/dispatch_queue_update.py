from fmlib.utils.messages import Document


class DispatchQueueUpdate:
    def __init__(self, zero_timepoint, dispatchable_graph, **kwargs):
        self.zero_timepoint = zero_timepoint
        self.dispatchable_graph = dispatchable_graph

    def to_dict(self):
        dict_repr = dict()
        dict_repr['zero_timepoint'] = self.zero_timepoint.to_str()
        dict_repr['dispatchable_graph'] = self.dispatchable_graph.to_dict()
        return dict_repr

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        task_queue_update = cls(**document)
        return task_queue_update

    @property
    def meta_model(self):
        return "dispatch-queue-update"
