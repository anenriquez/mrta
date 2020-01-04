from mrs.utils.as_dict import AsDictMixin


class TaskProgress(AsDictMixin):
    def __init__(self, task_id, robot_id, status, re_allocate_next=False):
        self.task_id = task_id
        self.robot_id = robot_id
        self.status = status
        self.re_allocate_next = re_allocate_next

    @property
    def meta_model(self):
        return "task-progress"


