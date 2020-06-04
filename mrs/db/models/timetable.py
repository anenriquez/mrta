import logging

import dateutil.parser
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
    solver_name = fields.CharField()
    ztp = fields.DateTimeField()
    stn = fields.DictField()
    dispatchable_graph = fields.DictField(default=dict())
    stn_tasks = fields.DictField(blank=True)

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
        document["ztp"] = dateutil.parser.parse(document.pop("ztp"))
        timetable = Timetable.from_document(document)
        return timetable

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        dict_repr["robot_id"] = str(dict_repr.pop('_id'))
        dict_repr["ztp"] = self.ztp.isoformat()
        return dict_repr
