from mrs.utils.as_dict import AsDictMixin


class RemoveTaskFromSchedule(AsDictMixin):
    def __init__(self, task_id, status):
        self.task_id = task_id
        self.status = status

    @property
    def meta_model(self):
        return "remove-task-from-schedule"
