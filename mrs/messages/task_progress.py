from mrs.utils.as_dict import AsDictMixin
from ropod.structs.status import ActionStatus


class ActionProgress(AsDictMixin):
    def __init__(self, action_id, **kwargs):
        self.action_id = action_id
        self.status = kwargs.get("status", ActionStatus.PLANNED)
        self.start_time = kwargs.get("start_time")
        self.finish_time = kwargs.get("finish_time")
        self.r_start_time = kwargs.get("r_start_time")
        self.r_finish_time = kwargs.get("r_finish_time")
        self.is_consistent = kwargs.get("is_consistent", True)

    def __str__(self):
        return "action id: {}, action status: {}, start time: {}, finish time: {}".format(self.action_id,
                                                                                          self.status,
                                                                                          self.start_time,
                                                                                          self.finish_time)

    def update(self, status, abs_time, r_time):
        self.status = status
        if self.start_time:
            self.finish_time = abs_time
            self.r_finish_time = r_time
        else:
            self.start_time = abs_time
            self.r_start_time = r_time


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
        attrs.update(action_progress=ActionProgress.from_dict(attrs.get("action_progress")))
        return attrs
