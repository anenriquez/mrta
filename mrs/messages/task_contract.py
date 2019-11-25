from fmlib.utils.messages import Document


class TaskContract(object):
    def __init__(self, task_id, robot_id, **kwargs):
        self.task_id = task_id
        self.robot_id = robot_id

    def to_dict(self):
        dict_repr = dict()
        dict_repr['task_id'] = self.task_id
        dict_repr['robot_id'] = self.robot_id
        return dict_repr

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        task_contract = cls(**document)
        return task_contract

    @property
    def meta_model(self):
        return "task-contract"

