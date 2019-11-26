class TaskContractAcknowledgment(object):
    def __init__(self, robot_id):
        self.robot_id = robot_id

    def to_dict(self):
        dict_repr = dict()
        dict_repr['robot_id'] = self.robot_id
        return dict_repr

    @property
    def meta_model(self):
        return "task-contract-acknowledgement"
