import datetime

from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid

from mrs.structs.status import TaskStatus
from mrs.utils.datasets import flatten_dict


class Task(object):

    def __init__(self, id=None,
                 earliest_start_time=-1,
                 latest_start_time=-1,
                 start_pose_name='',
                 finish_pose_name='',
                 **kwargs):

        """Constructor for the Task object

        Args:
            id (str): A string of the format UUID
            earliest_start_time (TimeStamp): The earliest a task can start
            latest_start_time (TimeStamp): The latest a task can start
            start_pose_name (str): The location where the robot should execute the task
            finish_pose_name (str): The location where the robot must terminate task execution
            estimated_duration (timedelta): A timedelta object specifying the duration
            hard_constraints (bool): False if the task can be
                                    scheduled ASAP, True if the task is not flexible. Defaults to True
        """

        if not id:
            self.id = generate_uuid()
        else:
            self.id = id

        self.earliest_start_time = earliest_start_time
        self.latest_start_time = latest_start_time
        self.start_pose_name = start_pose_name
        self.finish_pose_name = finish_pose_name
        self.hard_constraints = kwargs.get('hard_constraints', True)

        # Used by the dataset generator
        self.estimated_duration = kwargs.get('estimated_duration', -1)
        self.status = TaskStatus(id)

    def to_dict(self):
        task_dict = dict()
        task_dict['id'] = self.id
        task_dict['earliest_start_time'] = self.earliest_start_time.to_str()
        task_dict['latest_start_time'] = self.latest_start_time.to_str()
        task_dict['start_pose_name'] = self.start_pose_name
        task_dict['finish_pose_name'] = self.finish_pose_name
        task_dict['hard_constraints'] = self.hard_constraints
        task_dict['estimated_duration'] = self.estimated_duration.total_seconds() / 60  # Turn duration into minutes
        task_dict['status'] = self.status.to_dict()
        return task_dict

    @staticmethod
    def from_dict(task_dict):
        task = Task()
        task.id = task_dict['id']
        task.earliest_start_time = TimeStamp.from_str(task_dict['earliest_start_time'])
        task.latest_start_time = TimeStamp.from_str(task_dict['latest_start_time'])
        task.start_pose_name = task_dict['start_pose_name']
        task.finish_pose_name = task_dict['finish_pose_name']
        task.hard_constraints = task_dict['hard_constraints']
        task.estimated_duration = datetime.timedelta(minutes=task_dict['estimated_duration'])
        task.status = TaskStatus.from_dict(task_dict['status'])
        return task

    @staticmethod
    def to_csv(task_dict):
        """ Prepares dict to be written to a csv
        :return: dict
        """
        to_csv_dict = flatten_dict(task_dict)

        return to_csv_dict



