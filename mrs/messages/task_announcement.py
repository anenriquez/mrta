from fmlib.models.tasks import Task
from mrs.db.models.task import TaskLot
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid, from_str


class TaskAnnouncement(object):
    def __init__(self, tasks_lots, round_id, zero_timepoint):
        """
        Constructor for the TaskAnnouncement object

        Args:
             tasks_lots (list): List of TaskLot objects to be announced
             round_id (str): A string of the format UUID that identifies the round
             zero_timepoint (TimeStamp): Zero Time Point. Origin time to which task temporal information must be
                                        referenced to
        """
        self.tasks_lots = tasks_lots

        if not round_id:
            self.round_id = generate_uuid()
        else:
            self.round_id = round_id

        self.zero_timepoint = zero_timepoint

    def to_dict(self):
        dict_repr = dict()
        dict_repr['tasks_lots'] = dict()

        for task_lot in self.tasks_lots:
            dict_repr['tasks_lots'][str(task_lot.task.task_id)] = task_lot.to_dict()

        dict_repr['round_id'] = self.round_id
        dict_repr['zero_timepoint'] = self.zero_timepoint.to_str()

        return dict_repr

    @staticmethod
    def from_payload(payload):
        round_id = from_str(payload['roundId'])
        zero_timepoint = TimeStamp.from_str(payload['zeroTimepoint'])

        tasks_dict = payload['tasksLots']
        tasks_lots = list()

        for task_id, task_dict in tasks_dict.items():
            Task.create_new(task_id=task_id)
            tasks_lots.append(TaskLot.from_payload(task_dict))

        task_announcement = TaskAnnouncement(tasks_lots, round_id, zero_timepoint)

        return task_announcement

    @property
    def meta_model(self):
        return "task-announcement"

