from pymodm import fields, MongoModel


class BidTime(MongoModel):
    times_to_bid = fields.ListField()
    n_previously_allocated_tasks = fields.IntegerField()

    @classmethod
    def create_new(cls, **kwargs):
        bid_time = cls(**kwargs)
        bid_time.save()
        return bid_time
