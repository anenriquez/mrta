from fmlib.utils.messages import Document


class ArchiveTask:
    def __init__(self, robot_id, task_id, node_id, **kwargs):
        self.robot_id = robot_id
        self.task_id = task_id
        self.node_id = node_id

    def to_dict(self):
        dict_repr = dict()
        dict_repr['robot_id'] = self.robot_id
        dict_repr['task_id'] = self.task_id
        dict_repr['node_id'] = self.node_id
        return dict_repr

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        archive_task = cls(**document)
        return archive_task

    @property
    def meta_model(self):
        return "archive-task"

