import logging

from ropod.utils.uuid import generate_uuid
from ropod.structs.status import TaskStatus as TaskStatusConst
from pymodm.context_managers import switch_collection
from fleet_management.db.queries.sets.tasks import TaskStatusManager
from fleet_management.db.models.task import TaskStatus as RopodTaskStatus
from fleet_management.db.models.task import TaskConstraints, TimepointConstraints
from fleet_management.utils.messages import Document
from pymodm import fields, MongoModel
from pymongo.errors import ServerSelectionTimeoutError


class Task(MongoModel):
    task_id = fields.UUIDField(primary_key=True, default=generate_uuid())

    class Meta:
        archive_collection = 'task_archive'
        ignore_unknown_fields = True

    def save(self):
        try:
            super().save(cascade=True)
        except ServerSelectionTimeoutError:
            logging.warning('Could not save models to MongoDB')

    def archive(self):
        with switch_collection(Task, Task.Meta.archive_collection):
            super().save()
        self.delete()

    @classmethod
    def create(cls, task_id):
        task = cls(task_id)
        task.save()
        return task

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_msg(payload)
        document['_id'] = document.pop('task_id')
        task = Task.from_document(document)
        return task

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        dict_repr["task_id"] = str(dict_repr.pop('_id'))
        return dict_repr


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
        task_lot.update_status(TaskStatusConst.UNALLOCATED)

        return task_lot

    def update_status(self, status):
        status = TaskStatus(self.task_id, status)
        status.save()
        if status in [TaskStatusConst.COMPLETED, TaskStatusConst.CANCELED]:
            self.archive()
            status.archive()
            self.save()

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


class TaskStatus(RopodTaskStatus):
    task = fields.ReferenceField(TaskLot, primary_key=True, required=True)
    status = fields.IntegerField(default=TaskStatusConst.UNALLOCATED)
    delayed = fields.BooleanField(default=False)

    objects = TaskStatusManager()

