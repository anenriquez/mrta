from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid

from mrs.db.models.task import Task
from mrs.utils.as_dict import AsDictMixin


class TaskAnnouncement(AsDictMixin):
    def __init__(self, tasks, round_id, zero_timepoint):
        """
        Constructor for the TaskAnnouncement object

        Args:
             tasks (list): List of Task objects to be announced
             round_id (str): A string of the format UUID that identifies the round
             zero_timepoint (TimeStamp): Zero Time Point. Origin time to which task temporal information must be
                                        referenced to
        """
        self.tasks = tasks

        if not round_id:
            self.round_id = generate_uuid()
        else:
            self.round_id = round_id

        self.zero_timepoint = zero_timepoint

    def to_dict(self):
        dict_repr = super().to_dict()
        tasks_dict = dict()
        for task in self.tasks:
            tasks_dict[str(task.task_id)] = task.to_dict()
        dict_repr.update(tasks=tasks_dict)
        return dict_repr

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        tasks = list()
        for task_id, task_dict in attrs.get("tasks").items():
            tasks.append(Task.from_payload(task_dict))
        attrs.update(tasks=tasks)
        return attrs


    # @classmethod
    # def from_payload(cls, payload):
    #     document = Document.from_payload(payload)
    #     document.pop("metamodel")
    #     tasks = list()
    #     for task_id, task_dict in document.get("tasks").items():
    #         tasks.append(Task.from_payload(task_dict))
    #     document.update(tasks=tasks)
    #     document.update(round_id=from_str(document["round_id"]))
    #     document.update(zero_timepoint=TimeStamp.from_str(document["zero_timepoint"]))
    #
    #     print("----->Document")
    #     print(document)
    #     task_announcement = cls(**document)
    #     return task_announcement

        # round_id = from_str(payload['roundId'])
        # zero_timepoint = TimeStamp.from_str(payload['zeroTimepoint'])
        #
        # tasks_dict = payload['tasks']
        # tasks = list()
        #[
        # for task_id, task_dict in tasks_dict.items():
        #     tasks.append(Task.from_payload(task_dict))
        #
        # task_announcement = TaskAnnouncement(tasks, round_id, zero_timepoint)
        #
        # return task_announcement

    @property
    def meta_model(self):
        return "task-announcement"

