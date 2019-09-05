from pymodm import fields, MongoModel
from ropod.utils.uuid import generate_uuid


class Task(MongoModel):
    task_id = fields.UUIDField(primary_key=True, default=generate_uuid())

