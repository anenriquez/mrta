from mrs.utils.as_dict import AsDictMixin


class RecoverTask(AsDictMixin):
    def __init__(self, method, task_id, robot_id):
        self.method = method
        self.task_id = task_id
        self.robot_id = robot_id

    @property
    def meta_model(self):
        return "recover-task"
