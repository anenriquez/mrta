from stn.task import Task as STNTask

from mrs.db.models.actions import GoTo
from mrs.utils.as_dict import AsDictMixin


class TaskContract(AsDictMixin):
    def __init__(self, task_id, robot_id):
        self.task_id = task_id
        self.robot_id = robot_id

    @property
    def meta_model(self):
        return "task-contract"


class AllocationInfo(AsDictMixin):
    def __init__(self, insertion_point, stn_tasks, pre_task_actions):
        self.insertion_point = insertion_point
        self.stn_tasks = stn_tasks
        self.pre_task_actions = pre_task_actions
        self._stn = None
        self._dispatchable_graph = None

    @property
    def stn(self):
        return self._stn

    @stn.setter
    def stn(self, stn):
        self._stn = stn

    @property
    def dispatchable_graph(self):
        return self._dispatchable_graph

    @dispatchable_graph.setter
    def dispatchable_graph(self, dispatchable_graph):
        self._dispatchable_graph = dispatchable_graph

    def get_stn_tasks(self, task_id):
        new_stn_task = None
        next_stn_task = None
        for stn_task in self.stn_tasks:
            if stn_task.task_id == task_id:
                new_stn_task = stn_task
            else:
                next_stn_task = stn_task
        return new_stn_task, next_stn_task

    def to_dict(self):
        dict_repr = super().to_dict()
        stn_tasks = list()
        pre_task_actions = list()
        for task in self.stn_tasks:
            stn_tasks.append(task.to_dict())
        for action in self.pre_task_actions:
            pre_task_actions.append(action.to_dict())
        dict_repr.update(pre_task_actions=pre_task_actions)
        dict_repr.update(stn_tasks=stn_tasks)
        return dict_repr

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        stn_tasks = list()
        pre_task_actions = list()
        for task in attrs.get("stn_tasks"):
            stn_tasks.append(STNTask.from_dict(task))
        for action in attrs.get("pre_task_actions"):
            pre_task_actions.append(GoTo.from_payload(action))
        attrs.update(stn_tasks=stn_tasks)
        attrs.update(pre_task_actions=pre_task_actions)
        return attrs


class TaskContractAcknowledgment(TaskContract):
    def __init__(self, task_id, robot_id, allocation_info, accept=True):
        self.allocation_info = allocation_info
        super().__init__(task_id, robot_id)
        self.accept = accept

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        attrs.update(allocation_info=AllocationInfo.from_dict(dict_repr.get("allocation_info")))
        return attrs

    @property
    def meta_model(self):
        return "task-contract-acknowledgement"
