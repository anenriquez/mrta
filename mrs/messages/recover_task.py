from mrs.utils.as_dict import AsDictMixin


class RecoverTask(AsDictMixin):
    def __init__(self, method, task_id):
        self.method = method
        self.task_id = task_id

    @property
    def meta_model(self):
        return "recover"


# class ReAllocate(Recover):
#     def __init__(self, method, task_id):
#         super().__init__(method, task_id)
#
#     @property
#     def meta_model(self):
#         return "re-allocate"
#
#
# class Abort(Recover):
#     def __init__(self, method, task_id):
#         super().__init__(method, task_id)
#
#     @property
#     def meta_model(self):
#         return "abort"
#
#
# class ReSchedule(Recover):
#     def __init__(self, method, task_id):
#         super().__init__(method, task_id)
#
#     @property
#     def meta_model(self):
#         return "re-schedule"
