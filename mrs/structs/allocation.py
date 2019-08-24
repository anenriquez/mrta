from datetime import timedelta

from ropod.utils.uuid import generate_uuid
from ropod.utils.timestamp import TimeStamp


class TaskAnnouncement(object):
    def __init__(self, tasks, round_id, ztp):
        """
        Constructor for the TaskAnnouncement object

        Args:
             tasks (list): List of Task objects to be announced
             round_id (str): A string of the format UUID that identifies the round
             ztp (TimeStamp): Zero Time Point. Origin time to which task temporal information must be referenced to
        """
        self.tasks = tasks

        if not round_id:
            self.round_id = generate_uuid()
        else:
            self.round_id = round_id

        self.ztp = ztp

        delta = timedelta(minutes=1)
        self.earliest_navigation_start = TimeStamp(delta)

    def to_dict(self):
        task_annoucement_dict = dict()
        task_annoucement_dict['tasks'] = dict()

        for task in self.tasks:
            task_annoucement_dict['tasks'][task.id] = task.to_dict()

        task_annoucement_dict['round_id'] = self.round_id
        task_annoucement_dict['ztp'] = self.ztp.to_str()
        task_annoucement_dict['earliest_navigation_start'] = self.earliest_navigation_start

        return task_annoucement_dict

    @staticmethod
    def from_dict(task_annoucement_dict, task_cls):
        round_id = task_annoucement_dict['round_id']
        ztp = TimeStamp.from_str(task_annoucement_dict['ztp'])

        tasks_dict = task_annoucement_dict['tasks']
        tasks = list()
        for task_id, task_dict in tasks_dict.items():
            tasks.append(task_cls.from_dict(task_dict))

        task_announcement = TaskAnnouncement(tasks, round_id, ztp)
        task_announcement.earliest_navigation_start = task_annoucement_dict['earliest_navigation_start']

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
