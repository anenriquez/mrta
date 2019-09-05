from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid
from fleet_management.db.models.task import TaskConstraints, TimepointConstraints


class TaskLot:
    def __init__(self, task_id,
                 start_location,
                 finish_location,
                 earliest_start_time,
                 latest_start_time,
                 hard_constraints):

        self.task_id = str(task_id)
        self.start_location = start_location
        self.finish_location = finish_location

        start_timepoint_constraints = TimepointConstraints(earliest_time=earliest_start_time,
                                                           latest_time=latest_start_time)
        time_point_constraints = [start_timepoint_constraints]
        self.constraints = TaskConstraints(time_point_constraints=time_point_constraints,
                                           hard=hard_constraints)

    def to_dict(self):
        dict_repr = dict()
        dict_repr["task_id"] = self.task_id
        dict_repr["start_location"] = self.start_location
        dict_repr["finish_location"] = self.finish_location
        dict_repr["constraints"] = self.constraints.to_dict()

        return dict_repr

    @classmethod
    def from_dict(cls, task_dict):
        task_id = task_dict["task_id"]
        start_location = task_dict["start_location"]
        finish_location = task_dict["finish_location"]
        constraints = TaskConstraints.from_payload(task_dict["constraints"])

        start_timepoint_constraints = constraints.time_point_constraints[0]

        task = cls(task_id, start_location, finish_location, start_timepoint_constraints.earliest_time,
                   start_timepoint_constraints.latest_time, constraints.hard)

        return task

    @classmethod
    def from_request(cls, task_id, request):
        start_location = request.pickup_location
        finish_location = request.delivery_location
        earliest_start_time = request.earliest_pickup_time
        latest_start_time = request.latest_pickup_time
        hard_constraints = request.hard_constraints
        task = cls(task_id, start_location, finish_location, earliest_start_time,
                   latest_start_time, hard_constraints)
        return task


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
            task_announcement_dict['tasks_lots'][task_lot.task_id] = task_lot.to_dict()

        task_announcement_dict['round_id'] = self.round_id
        task_announcement_dict['zero_timepoint'] = self.zero_timepoint.to_str()

        return task_announcement_dict

    @staticmethod
    def from_dict(task_announcement_dict):
        round_id = task_announcement_dict['round_id']
        zero_timepoint = TimeStamp.from_str(task_announcement_dict['zero_timepoint'])

        tasks_dict = task_announcement_dict['tasks_lots']
        tasks_lots = list()

        for task_id, task_dict in tasks_dict.items():
            tasks_lots.append(TaskLot.from_dict(task_dict))

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
