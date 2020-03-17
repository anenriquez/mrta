from mrs.db.models.actions import ActionProgress
from mrs.utils.as_dict import AsDictMixin


class ActionStatus(AsDictMixin):
    def __init__(self, status, **kwargs):
        self.status = status
        self.domain = kwargs.get("domain")
        self.module = kwargs.get("module")


class TaskProgress(AsDictMixin):
    def __init__(self, action_id, action_type, action_status):
        self.action_id = action_id
        self.action_type = action_type
        self.action_status = action_status

    # def to_dict(self):
    #     dict_repr = super().to_dict()
    #     dict_repr.update(action_status=self.action_status.to_dict())

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        attrs.update(action_status=ActionStatus.from_payload(attrs.get("action_status")))
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
        attrs.update(task_progress=TaskProgress.from_payload(attrs.get("task_progress")))
        return attrs
