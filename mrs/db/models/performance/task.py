import logging

from pymodm import fields, EmbeddedMongoModel, MongoModel
from ropod.utils.uuid import generate_uuid
from pymongo.errors import ServerSelectionTimeoutError
from pymodm.context_managers import switch_collection
from fleet_management.utils.messages import Document


class TaskAllocationPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to allocation

    allocated (bool):   indicates whether a task was allocated or not

    n_re_allocation_attempts (int): number of times the system attempted to re-allocate the task

    allocation_time (list): List of floats. The first entry indicates the time
                            taken to allocate the task for the first time. Successive
                            entries indicate the re-allocation time for each re-allocation.
    """
    allocated = fields.BooleanField()
    n_re_allocation_attempts = fields.IntegerField()
    allocation_time = fields.ListField()


class TaskSchedulingPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to scheduling

    work_time (float):  scheduled time to perform the task.
                        E.g.  For a transportation task, time to transport an object
                        from the pickup to the delivery location

    travel_time (float): scheduled time to reach the task location
                        E.g. For a transportation task, time to go from current position
                        to pickup location

    n_re_scheduling_attempts (int): number of times the system attempted to re-schedule the task

    scheduling_time (list): List of floats. The first entry indicates the time taken to
                            schedule the task for the first time. Successive entries indicate
                            the re-scheduling time for each re-schedule.

    """
    work_time = fields.FloatField()
    travel_time = fields.FloatField()
    n_re_scheduling_attempts = fields.IntegerField()
    scheduling_time = fields.ListField()


class TaskExecutionPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to execution

    work_time (float):  time taken to perform the task.
                        E.g.  For a transportation task, time to transport an object
                        from the pickup to the delivery location

    travel_time (float): time taken to reach the task location
                        E.g. For a transportation task, time to go from current position
                        to pickup location

    executed (bool):    indicates whether a task was executed or not

    delayed (bool): false if the task was executed without violating its temporal constraints,
                    otherwise true
    """
    work_time = fields.FloatField()
    travel_time = fields.FloatField()
    executed = fields.BooleanField()
    delayed = fields.BooleanField()


class TaskPerformance(MongoModel):
    """ Stores task performance information:

    task_id (UUID):     uniquely identifies the task
    allocation (TaskAllocationPerformance):  task performance metrics related to allocation
    scheduling (TaskSchedulingPerformance):  task performance metrics related to scheduling
    execution (TaskExecutionPerformance):  task performance metrics related to execution

    """
    task_id = fields.UUIDField(primary_key=True, default=generate_uuid())
    allocation = fields.EmbeddedDocumentField(TaskAllocationPerformance)
    scheduling = fields.EmbeddedDocumentField(TaskSchedulingPerformance)
    execution = fields.EmbeddedDocumentField(TaskExecutionPerformance)

    class Meta:
        archive_collection = 'task_performance_archive'
        ignore_unknown_fields = True

    def save(self):
        try:
            super().save(cascade=True)
        except ServerSelectionTimeoutError:
            logging.warning('Could not save models to MongoDB')

    def archive(self):
        with switch_collection(TaskPerformance, TaskPerformance.Meta.archive_collection):
            super().save()
        self.delete()

    @classmethod
    def create(cls, task_id):
        performance = cls(task_id)
        performance.save()
        return performance

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_msg(payload)
        document['_id'] = document.pop('task_id')
        performance = TaskPerformance.from_document(document)
        return performance

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        dict_repr["task_id"] = str(dict_repr.pop('_id'))
        return dict_repr



