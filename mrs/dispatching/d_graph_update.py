from fmlib.utils.messages import Document


class DGraphUpdate:
    def __init__(self, dispatchable_graph, **kwargs):
        self.dispatchable_graph = dispatchable_graph

    def to_dict(self):
        dict_repr = dict()
        dict_repr['dispatchable_graph'] = self.dispatchable_graph.to_dict()
        return dict_repr

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        task_queue_update = cls(**document)
        return task_queue_update

    @property
    def meta_model(self):
        return "d-graph-update"