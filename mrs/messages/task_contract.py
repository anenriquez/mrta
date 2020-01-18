from mrs.utils.as_dict import AsDictMixin


class TaskContract(AsDictMixin):
    def __init__(self, task_id, robot_id):
        self.task_id = task_id
        self.robot_id = robot_id

    @property
    def meta_model(self):
        return "task-contract"


class TaskContractAcknowledgment(TaskContract):
    def __init__(self, task_id, robot_id, accept=True):
        super().__init__(task_id, robot_id)
        self.accept = accept

    @property
    def meta_model(self):
        return "task-contract-acknowledgement"

