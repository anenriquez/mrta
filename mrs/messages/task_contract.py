from mrs.utils.as_dict import AsDictMixin


class TaskContract(AsDictMixin):
    def __init__(self, task_id, robot_id):
        self.task_id = task_id
        self.robot_id = robot_id

    @property
    def meta_model(self):
        return "task-contract"

    @staticmethod
    def is_valid(n_tasks_before, n_tasks_after):
        if n_tasks_after - n_tasks_before == 1:
            return True
        return False


class TaskContractAcknowledgment(TaskContract):
    def __init__(self, task_id, robot_id, n_tasks, accept=True):
        super().__init__(task_id, robot_id)
        self.accept = accept
        self.n_tasks = n_tasks  # Number of tasks in the robot_id's stn, including task_id

    @property
    def meta_model(self):
        return "task-contract-acknowledgement"

