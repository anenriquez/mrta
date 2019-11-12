from fmlib.utils.messages import Document


class DispatchRequest:

    def __init__(self, task_id, **kwargs):
        self.task_id = task_id

    def to_dict(self):
        dict_repr = dict()
        dict_repr['task_id'] = self.task_id
        return dict_repr

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        dispatch_request = cls(**document)
        return dispatch_request

    @property
    def meta_model(self):
        return "dispatch-request"


