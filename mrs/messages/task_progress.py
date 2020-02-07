from mrs.db.models.actions import ActionProgress
from mrs.utils.as_dict import AsDictMixin


class TaskProgress(AsDictMixin):
    def __init__(self, task_id, status, robot_id, action_progress):
        self.task_id = task_id
        self.status = status
        self.robot_id = robot_id
        self.action_progress = action_progress

    def __str__(self):
        return "task id: {}, status: {} \n {}".format(self.task_id, self.status, self.action_progress)

    @property
    def meta_model(self):
        return "task-progress"

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        attrs.update(action_progress=ActionProgress.from_payload(attrs.get("action_progress")))
        return attrs
