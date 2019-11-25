from ropod.utils.uuid import from_str


class Allocation(object):
    def __init__(self, task_id, robot_id):
        self.task_id = task_id
        self.robot_id = robot_id

    def to_dict(self):
        dict_repr = dict()
        dict_repr['task_id'] = self.task_id
        dict_repr['robot_id'] = self.robot_id

        return dict_repr

    @staticmethod
    def from_payload(payload):
        allocation = Allocation
        allocation.task_id = from_str(payload['taskId'])
        allocation.robot_id = payload['robotId']

        return allocation

    @property
    def meta_model(self):
        return "allocation"

