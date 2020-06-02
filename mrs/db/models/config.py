from pymodm import fields, MongoModel
from pymodm.queryset import QuerySet
from pymodm.manager import Manager


class ConfigQuerySet(QuerySet):
    def get_config(self, component_name):
        return self.get({'_id': component_name})


TimetableManager = Manager.from_queryset(ConfigQuerySet)


class Config(MongoModel):
    component_name = fields.CharField(primary_key=True)
    config_params = fields.DictField()

    @classmethod
    def create_new(cls, component_name, config_params):
        config = cls(component_name, config_params)
        config.save()
