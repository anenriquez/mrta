import logging

from fmlib.utils.messages import Document
from pymodm import fields, MongoModel
from pymodm.manager import Manager
from pymodm.queryset import QuerySet
from pymongo.errors import ServerSelectionTimeoutError


class TimetableQuerySet(QuerySet):
    def get_timetable(self, robot_id):
        """ Returns a timetable mongo model that matches to the robot_id
        """
        return self.get({'_id': robot_id})


TimetableManager = Manager.from_queryset(TimetableQuerySet)


class Timetable(MongoModel):
    robot_id = fields.CharField(primary_key=True)
    zero_timepoint = fields.DateTimeField()
    temporal_metric = fields.FloatField()
    risk_metric = fields.FloatField()
    stn = fields.DictField()
    dispatchable_graph = fields.DictField(default=dict())

    objects = TimetableManager()

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
        document = Document.from_payload(payload)
        document['_id'] = document.pop('robot_id')
        timetable = Timetable.from_document(document)
        return timetable

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        dict_repr["robot_id"] = str(dict_repr.pop('_id'))
        return dict_repr
