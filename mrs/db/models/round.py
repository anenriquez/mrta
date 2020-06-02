from pymodm import fields, MongoModel
from pymodm.queryset import QuerySet
from pymodm.manager import Manager


class RoundQuerySet(QuerySet):

    def get_task(self, number):
        return self.get({'_id': number})


RoundManager = Manager.from_queryset(RoundQuerySet)


class Round(MongoModel):
    number = fields.IntegerField(primary_key=True)
    round_id = fields.CharField()
    tasks_to_allocate = fields.ListField(blank=True)
    time_to_allocate = fields.FloatField()
    allocated_task = fields.UUIDField()
    n_received_bids = fields.IntegerField()
    n_received_no_bids = fields.IntegerField()

    objects = RoundManager()

    class Meta:
        ignore_unknown_fields = True

    @classmethod
    def create_new(cls, **kwargs):
        kwargs.update(number=cls.get_number())
        round_ = cls(**kwargs)
        round_.save()
        return round_

    @classmethod
    def get_number(cls):
        numbers = [round_.number for round_ in cls.objects.all()]
        if numbers:
            previous_number = numbers.pop()
            number = previous_number + 1
        else:
            number = 1
        return number



