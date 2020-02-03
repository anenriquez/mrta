from mrs.utils.as_dict import AsDictMixin


class ReAllocate(AsDictMixin):
    def __init__(self, task_id):
        self.task_id = task_id

    @property
    def meta_model(self):
        return "re-allocate"
