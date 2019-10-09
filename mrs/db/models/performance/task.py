import logging

from fmlib.models.tasks import Task
from fmlib.utils.messages import Document
from pymodm import fields, EmbeddedMongoModel, MongoModel
from pymodm.context_managers import switch_collection
from pymongo.errors import ServerSelectionTimeoutError
from fmlib.models.tasks import TaskManager


class TaskAllocationPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to allocation

    allocated (bool):   indicates whether a task was allocated or not

    n_re_allocation_attempts (int): number of times the system attempted to re-allocate the task

    allocation_time (list): List of floats. The first entry indicates the time
                            taken to allocate the task for the first time. Successive
                            entries indicate the re-allocation time for each re-allocation.

    robot_id: robot id of the robot that allocated the task

    """
    allocated = fields.BooleanField(default=False)
    n_re_allocation_attempts = fields.IntegerField(default=0)
    allocation_time = fields.ListField()
    robot_id = fields.CharField()


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
    n_re_scheduling_attempts = fields.IntegerField(default=0)
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
    executed = fields.BooleanField(default=False)
    delayed = fields.BooleanField(default=False)


class TaskPerformance(MongoModel):
    """ Stores task performance information:

    task_id (UUID):     uniquely identifies the task
    allocation (TaskAllocationPerformance):  task performance metrics related to allocation
    scheduling (TaskSchedulingPerformance):  task performance metrics related to scheduling
    execution (TaskExecutionPerformance):  task performance metrics related to execution

    """
    task = fields.ReferenceField(Task, primary_key=True)
    allocation = fields.EmbeddedDocumentField(TaskAllocationPerformance, default=TaskAllocationPerformance())
    scheduling = fields.EmbeddedDocumentField(TaskSchedulingPerformance, default=TaskSchedulingPerformance())
    execution = fields.EmbeddedDocumentField(TaskExecutionPerformance, default=TaskExecutionPerformance())

    objects = TaskManager()

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
    def create(cls, task):
        performance = cls(task)
        performance.save()
        return performance

    @classmethod
    def get_task(cls, task_id):
        return cls.objects.get_task(task_id)

    def update_allocation(self, allocation_time, robot_id, allocated=True):
        self.allocation.allocated = allocated
        self.allocation.n_re_allocation_attempts += 1
        self.allocation.allocation_time = allocation_time
        self.allocation.robot_id = robot_id
        self.save()

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        document['_id'] = document.pop('task_id')
        performance = TaskPerformance.from_document(document)
        return performance

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        dict_repr["task_id"] = str(dict_repr.pop('_id'))
        return dict_repr
