from mrs.utils.as_dict import AsDictMixin


class ArchiveTask(AsDictMixin):
    def __init__(self, robot_id, task_id, node_id, **kwargs):
        self.robot_id = robot_id
        self.task_id = task_id
        self.node_id = node_id

    @property
    def meta_model(self):
        return "archive-task"

