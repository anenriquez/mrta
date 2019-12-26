from mrs.utils.as_dict import AsDictMixin


class TaskContract(AsDictMixin):
    def __init__(self, task_id, robot_id, **kwargs):
        self.task_id = task_id
        self.robot_id = robot_id

    @property
    def meta_model(self):
        return "task-contract"


class TaskContractAcknowledgment(AsDictMixin):
    def __init__(self, robot_id):
        self.robot_id = robot_id

    @property
    def meta_model(self):
        return "task-contract-acknowledgement"

