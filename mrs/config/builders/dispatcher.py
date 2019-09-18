from mrs.task_execution.dispatcher import Dispatcher


class DispatcherBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, **kwargs):
        if not self._instance:
            self._instance = Dispatcher(**kwargs)
        return self._instance


configure = DispatcherBuilder()
