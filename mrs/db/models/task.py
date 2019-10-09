import logging

from fmlib.models.tasks import Task
from fmlib.models.tasks import TaskConstraints, TimepointConstraints
from fmlib.utils.messages import Document
from pymodm import fields, MongoModel
from pymongo.errors import ServerSelectionTimeoutError
from ropod.structs.status import TaskStatus as TaskStatusConst
from fmlib.models.tasks import TaskManager


class TaskLot(MongoModel):
    task = fields.ReferenceField(Task, primary_key=True)
    start_location = fields.CharField()
    finish_location = fields.CharField()
    constraints = fields.EmbeddedDocumentField(TaskConstraints)

    objects = TaskManager()

    class Meta:
        archive_collection = 'task_lot_archive'
        ignore_unknown_fields = True

    def save(self):
        try:
            super().save(cascade=True)
        except ServerSelectionTimeoutError:
            logging.warning('Could not save models to MongoDB')

    @classmethod
    def create(cls, task,
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

        task_lot = cls(task=task, start_location=start_location,
                       finish_location=finish_location, constraints=constraints)
        task_lot.save()
        task_lot.task.update_status(TaskStatusConst.UNALLOCATED)

        return task_lot

    @classmethod
    def get_task(cls, task_id):
        return cls.objects.get_task(task_id)

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
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
    def from_task(cls, task):
        start_location = task.request.pickup_location
        finish_location = task.request.delivery_location
        earliest_start_time = task.request.earliest_pickup_time
        latest_start_time = task.request.latest_pickup_time
        hard_constraints = task.request.hard_constraints
        task_lot = TaskLot.create(task, start_location, finish_location, earliest_start_time,
                                  latest_start_time, hard_constraints)
        return task_lot
