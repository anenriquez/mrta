import logging

from fleet_management.utils.messages import Document
from pymodm import fields, MongoModel
from pymongo.errors import ServerSelectionTimeoutError
from ropod.utils.uuid import generate_uuid


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
