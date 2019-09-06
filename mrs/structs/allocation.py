import logging

from fleet_management.db.models.task import TaskConstraints, TimepointConstraints
from fleet_management.utils.messages import Document
from pymodm import fields, MongoModel
from pymongo.errors import ServerSelectionTimeoutError
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid, from_str


class TaskLot(MongoModel):
    task_id = fields.UUIDField(primary_key=True)
    start_location = fields.CharField()
    finish_location = fields.CharField()
    constraints = fields.EmbeddedDocumentField(TaskConstraints)

    class Meta:
        archive_collection = 'task_lot_archive'
        ignore_unknown_fields = True

    def save(self):
        try:
            super().save(cascade=True)
        except ServerSelectionTimeoutError:
            logging.warning('Could not save models to MongoDB')

    @classmethod
    def create(cls, task_id,
               start_location,
               finish_location,
               earliest_start_time,
               latest_start_time,
               hard_constraints):

        start_timepoint_constraints = TimepointConstraints(earliest_time=earliest_start_time,
                                                           latest_time=latest_start_time)
        timepoint_constraints = [start_timepoint_constraints]

        constraints = TaskConstraints(timepoint_constraints=timepoint_constraints,
                                      hard=hard_constraints)

        task_lot = cls(task_id, start_location, finish_location, constraints)
        task_lot.save()

        return task_lot

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_msg(payload)
        document['_id'] = document.pop('task_id')
        document["constraints"] = TaskConstraints.from_payload(document.pop("constraints"))
        task_lot = TaskLot.from_document(document)
        return task_lot

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        dict_repr["task_id"] = str(dict_repr.pop('_id'))
        dict_repr["constraints"] = self.constraints.to_dict()
        return dict_repr

    @classmethod
    def from_request(cls, task_id, request):
        start_location = request.pickup_location
        finish_location = request.delivery_location
        earliest_start_time = request.earliest_pickup_time
        latest_start_time = request.latest_pickup_time
        hard_constraints = request.hard_constraints
        task_lot = TaskLot.create(task_id, start_location, finish_location, earliest_start_time,
                       latest_start_time, hard_constraints)
        return task_lot


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
