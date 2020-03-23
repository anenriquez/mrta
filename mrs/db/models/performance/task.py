from fmlib.models.tasks import TaskManager as TaskPerformanceManager
from fmlib.utils.messages import Document
from pymodm import fields, EmbeddedMongoModel, MongoModel


class TaskAllocationPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to allocation

    time_to_allocate (float): Time taken to allocate the task

    n_previously_allocated_tasks (int): Number of task in the robot's STN before allocating this task

    travel_time_boundaries ([float, float]): [min, max]
                                           Travel time constraint boundaries in the d-graph, i.e.,
                                           minimum and maximum time to start and complete the
                                           ROBOT-TO-PICKUP action

    work_time_boundaries ([float, float]): [min, max]
                                       Work time constraint boundaries in the d-graph, i.e.,
                                       minimum and maximum time to start and complete the
                                       PICKUP-TO-DELIVERY action
    """
    time_to_allocate = fields.ListField()
    n_previously_allocated_tasks = fields.ListField()
    travel_time_boundaries = fields.ListField()
    work_time_boundaries = fields.ListField()
    n_re_allocation_attempts = fields.IntegerField(default=0)
    allocated = fields.BooleanField(default=False)

    def initialize(self):
        self.time_to_allocate = list()
        self.n_previously_allocated_tasks = list()

    def update(self, **kwargs):
        if 'time_to_allocate' in kwargs:
            self.time_to_allocate.append(kwargs['time_to_allocate'])
        if 'n_previously_allocated_tasks' in kwargs:
            self.n_previously_allocated_tasks.append(kwargs['n_previously_allocated_tasks'])
        if 'travel_time_boundaries' in kwargs:
            self.travel_time_boundaries = kwargs['travel_time_boundaries']
        if 'work_time_boundaries' in kwargs:
            self.work_time_boundaries = kwargs['work_time_boundaries']


class TaskExecutionPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to execution

    travel_time (float): Time taken to reach the task location, i.e,
                        Time to go from current position to pickup location

    work_time (float):  Time taken to perform the task. i.e,
                        Time to transport an object from the pickup to the delivery location

    delay (float): Time (in seconds) between latest admissible time and execution time
                  (if the execution time is later than the latest admissible time)
                   for all timepoints in the dispatchable graph


    earliness (float): Time (in seconds) between the execution time and earliest admissible
                       (if the execution time is earlier than the earliest admissible time)
                       for all timepoints in the dispatchable graph
    """
    travel_time = fields.FloatField()
    work_time = fields.FloatField()
    delay = fields.FloatField(default=0.0)
    earliness = fields.FloatField(default=0.0)

    def update(self, travel_time, work_time):
        self.travel_time = travel_time
        self.work_time = work_time


class TaskPerformance(MongoModel):
    """ Stores task performance information:

    task (Task): Reference to Task object
    allocation (TaskAllocationPerformance):  Task performance metrics related to allocation
    execution (TaskExecutionPerformance):  Task performance metrics related to execution

    """
    task_id = fields.UUIDField(primary_key=True, required=True)
    allocation = fields.EmbeddedDocumentField(TaskAllocationPerformance)
    execution = fields.EmbeddedDocumentField(TaskExecutionPerformance)

    objects = TaskPerformanceManager()

    class Meta:
        ignore_unknown_fields = True
        meta_model = "task-performance"

    @classmethod
    def create_new(cls, task_id):
        performance = cls(task_id=task_id)
        performance.save()
        return performance

    def update_allocation(self, **kwargs):
        if not self.allocation:
            self.allocation = TaskAllocationPerformance()
            self.allocation.initialize()
        self.allocation.update(**kwargs)
        self.save(cascade=True)

    def update_execution(self, travel_time, work_time):
        if not self.execution:
            self.execution = TaskExecutionPerformance()
        self.execution.update(travel_time, work_time)
        self.save(cascade=True)

    def update_delay(self, delay):
        if not self.execution:
            self.execution = TaskExecutionPerformance()
        self.execution.delay += delay
        self.save(cascade=True)

    def update_earliness(self, earliness):
        if not self.execution:
            self.execution = TaskExecutionPerformance()
        self.execution.earliness += earliness
        self.save(cascade=True)

    def increase_n_re_allocation_attempts(self):
        self.allocation.n_re_allocation_attempts += 1
        self.save(cascade=True)

    def allocated(self):
        self.allocation.allocated = True
        self.save(cascade=True)

    def unallocated(self):
        self.allocation.allocated = False
        self.save(cascade=True)

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

    @classmethod
    def get_task_performance(cls, task_id):
        return cls.objects.get_task(task_id)

    @property
    def meta_model(self):
        return self.Meta.meta_model
