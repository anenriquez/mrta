from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid, from_str
from mrs.models.task import TaskLot


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
        task_announcement_dict = dict()
        task_announcement_dict['tasks_lots'] = dict()

        for task_lot in self.tasks_lots:
            task_announcement_dict['tasks_lots'][str(task_lot.task_id)] = task_lot.to_dict()

        task_announcement_dict['round_id'] = self.round_id
        task_announcement_dict['zero_timepoint'] = self.zero_timepoint.to_str()

        return task_announcement_dict

    @staticmethod
    def from_dict(task_announcement_dict):
        round_id = from_str(task_announcement_dict['round_id'])
        zero_timepoint = TimeStamp.from_str(task_announcement_dict['zero_timepoint'])

        tasks_dict = task_announcement_dict['tasks_lots']
        tasks_lots = list()

        for task_id, task_dict in tasks_dict.items():
            tasks_lots.append(TaskLot.from_payload(task_dict))

        task_announcement = TaskAnnouncement(tasks_lots, round_id, zero_timepoint)

        return task_announcement


class Allocation(object):
    def __init__(self, task_id, robot_id):
        self.task_id = task_id
        self.robot_id = robot_id

    def to_dict(self):
        allocation_dict = dict()
        allocation_dict['task_id'] = self.task_id
        allocation_dict['robot_id'] = self.robot_id
        return allocation_dict


class FinishRound(object):
    def __init__(self, robot_id):
        self.robot_id = robot_id

    def to_dict(self):
        finish_round = dict()
        finish_round['robot_id'] = self.robot_id
        return finish_round
