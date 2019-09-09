from pymodm import fields, MongoModel
from pymongo.errors import ServerSelectionTimeoutError
from fleet_management.utils.messages import Document
import logging


class Timetable(MongoModel):
    robot_id = fields.CharField(primary_key=True)
    zero_timepoint = fields.DateTimeField()
    stn = fields.DictField()
    dispatchable_graph = fields.DictField(default=dict())

    class Meta:
        archive_collection = 'timetable_archive'
        ignore_unknown_fields = True

    def save(self):
        try:
            super().save(cascade=True)
        except ServerSelectionTimeoutError:
            logging.warning('Could not save models to MongoDB')

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_msg(payload)
        document['_id'] = document.pop('robot_id')
        timetable = Timetable.from_document(document)
        return timetable

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        dict_repr["robot_id"] = str(dict_repr.pop('_id'))
        return dict_repr
