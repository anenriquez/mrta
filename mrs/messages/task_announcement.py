from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid, from_str

from mrs.db.models.task import Task
from datetime import datetime


class TaskAnnouncement(object):
    def __init__(self, tasks, round_id, zero_timepoint):
        """
        Constructor for the TaskAnnouncement object

        Args:
             tasks (list): List of TransportationTask objects to be announced
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

    def get_earliest_task(self):
        earliest_time = datetime.max
        for task in self.tasks:
            timepoint_constraints = task.get_timepoint_constraints()
            for constraint in timepoint_constraints:
                if constraint.earliest_time < earliest_time:
                    earliest_time = constraint.earliest_time
        return earliest_time

    def to_dict(self):
        dict_repr = dict()
        dict_repr['tasks'] = dict()

        for task in self.tasks:
            dict_repr['tasks'][str(task.task_id)] = task.to_dict()

        dict_repr['round_id'] = self.round_id
        dict_repr['zero_timepoint'] = self.zero_timepoint.to_str()

        return dict_repr

    @staticmethod
    def from_payload(payload):
        round_id = from_str(payload['roundId'])
        zero_timepoint = TimeStamp.from_str(payload['zeroTimepoint'])

        tasks_dict = payload['tasks']
        tasks = list()

        for task_id, task_dict in tasks_dict.items():
            tasks.append(Task.from_payload(task_dict))

        task_announcement = TaskAnnouncement(tasks, round_id, zero_timepoint)

        return task_announcement

    @property
    def meta_model(self):
        return "task-announcement"

