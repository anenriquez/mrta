from ropod.structs.status import ActionStatus as ActionStatusConst

from mrs.utils.as_dict import AsDictMixin


class ActionStatus(AsDictMixin):
    def __init__(self, status, **kwargs):
        self.status = status
        self.domain = kwargs.get("domain")
        self.module = kwargs.get("module")

    def update(self, status):
        self.status = status


class TaskProgress(AsDictMixin):
    def __init__(self, action_id, action_type, **kwargs):
        self.action_id = action_id
        self.action_type = action_type
        self.action_status = kwargs.get("action_status", ActionStatus(ActionStatusConst.PLANNED))

        # In simulation, we set the timestamp
        self._timestamp = None
        # Used by the ScheduleMonitor
        self._is_consistent = True

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp = timestamp

    @property
    def is_consistent(self):
        return self._is_consistent

    @is_consistent.setter
    def is_consistent(self, is_consistent):
        self._is_consistent = is_consistent

    def update_action_status(self, status):
        self.action_status.update(status)

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        attrs.update(action_status=ActionStatus.from_dict(attrs.get("action_status")))
        return attrs


class TaskStatus(AsDictMixin):
    def __init__(self, task_id, robot_id, task_status, task_progress, delayed=False):
        self.task_id = task_id
        self.robot_id = robot_id
        self.task_status = task_status
        self.task_progress = task_progress
        self.delayed = delayed

    @property
    def meta_model(self):
        return "task-status"

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        attrs.update(task_progress=TaskProgress.from_dict(attrs.get("task_progress")))
        return attrs
