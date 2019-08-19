from importlib import import_module


class TaskFactory(object):
    def __init__(self):
        self._task_cls = {}
        self.initialize()

    def register_task_cls(self, task_type, task_cls):
        self._task_cls[task_type] = task_cls

    def get_task_cls(self, task_type):
        task_cls = self._task_cls.get(task_type)
        if not task_cls:
            raise ValueError(task_type)

        return task_cls

    def initialize(self):
        ropod_task_cls = getattr(import_module('ropod.structs.task'), 'Task')
        self.register_task_cls('ropod_task', ropod_task_cls)

        generic_task_cls = getattr(import_module('mrs.structs.task'), 'Task')
        self.register_task_cls('generic_task', generic_task_cls)

        task_request_cls = getattr(import_module('ropod.structs.task'), 'TaskRequest')
        self.register_task_cls('task_request', task_request_cls)
