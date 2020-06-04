from mrs.messages.bid import AllocationInfo
from mrs.utils.as_dict import AsDictMixin
from stn.task import Task as STNTask


class TaskContract(AsDictMixin):
    def __init__(self, task_id, robot_id):
        self.task_id = task_id
        self.robot_id = robot_id

    @property
    def meta_model(self):
        return "task-contract"


class TaskContractAcknowledgment(TaskContract):
    def __init__(self, task_id, robot_id, allocation_info, accept=True):
        super().__init__(task_id, robot_id)
        self.allocation_info = allocation_info
        self.accept = accept

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        attrs.update(allocation_info=AllocationInfo.from_dict(dict_repr.get("allocation_info")))
        return attrs

    @property
    def meta_model(self):
        return "task-contract-acknowledgement"


class TaskContractCancellation(TaskContract):
    def __init__(self, task_id, robot_id, prev_version_next_task=None):
        super().__init__(task_id, robot_id)
        self.prev_version_next_task = prev_version_next_task

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        prev_version_next_task = attrs.get("prev_version_next_task")
        if prev_version_next_task:
            attrs.update(prev_version_next_task=STNTask.from_dict(prev_version_next_task))
        return attrs

    @property
    def meta_model(self):
        return "task-contract-cancellation"
