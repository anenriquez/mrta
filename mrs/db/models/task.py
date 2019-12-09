import logging

from fmlib.models.requests import TransportationRequest
from fmlib.models.tasks import Task
from fmlib.models.tasks import TaskManager
from fmlib.utils.messages import Document
from pymodm import fields, MongoModel
from pymongo.errors import ServerSelectionTimeoutError
from ropod.structs.status import TaskStatus as TaskStatusConst


class TaskLot(MongoModel):
    task = fields.ReferenceField(Task, primary_key=True)
    frozen = fields.BooleanField(default=False)

    objects = TaskManager()

    class Meta:
        archive_collection = "task_lot_archive"
        ignore_unknown_fields = True

    def save(self):
        try:
            super().save(cascade=True)
        except ServerSelectionTimeoutError:
            logging.warning("Could not save models to MongoDB")

    @classmethod
    def create_new(cls, task):
        task_lot = cls(task=task)
        task_lot.save()
        task_lot.task.update_status(TaskStatusConst.UNALLOCATED)

        return task_lot

    @classmethod
    def get_task(cls, task_id):
        return cls.objects.get_task(task_id)

    def set_soft_constraints(self):
        self.constraints.hard = False
        self.save()

    @classmethod
    def freeze_task(cls, task_id):
        task = cls.get_task(task_id)
        task.frozen = True
        task.save()

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        document["task"] = Task.from_payload(document.pop("task"))
        document["request"] = TransportationRequest.from_payload(document.pop("request"))
        task_lot = TaskLot.from_document(document)
        task_lot.save()
        return task_lot

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop("_cls")
        dict_repr["task"] = self.task.to_dict()
        dict_repr["request"] = self.task.request.to_dict()
        return dict_repr

