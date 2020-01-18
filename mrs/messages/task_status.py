from mrs.utils.as_dict import AsDictMixin


class TaskStatus(AsDictMixin):
    def __init__(self, task_id, robot_id, status, delayed):
        self.task_id = task_id
        self.robot_id = robot_id
        self.status = status
        self.delayed = delayed

    @property
    def meta_model(self):
        return "task-status"
