from fmlib.models.tasks import TaskManager as TaskPerformanceManager, TimepointConstraint
from fmlib.utils.messages import Document
from pymodm import fields, EmbeddedMongoModel, MongoModel


class TaskAllocationPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to allocation

    time_to_allocate (float): Time taken to allocate the task

    n_previously_allocated_tasks (int): Number of task in the robot's STN before allocating this task

    timepoint constraints of d-graph after allocation:
        start_time (TimepointConstraint): earliest and latest time for the timepoint 'start'
        pickup_time (TimepointConstraint): earliest and latest time for the timepoint 'pickup'
        delivery_time (TimepointConstraint): earliest and latest time for the timepoint 'delivery'

    n_re_allocation_attempts (int): Number of times the system tried to re-allocate the task
    allocated(boolean): Indicates whether the task was allocated or not

    """
    time_to_allocate = fields.ListField()
    n_previously_allocated_tasks = fields.ListField()
    start_time = fields.EmbeddedDocumentField(TimepointConstraint)
    pickup_time = fields.EmbeddedDocumentField(TimepointConstraint)
    delivery_time = fields.EmbeddedDocumentField(TimepointConstraint)
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
        if 'start_time' in kwargs:
            self.start_time = kwargs['start_time']
        if 'pickup_time' in kwargs:
            self.pickup_time = kwargs['pickup_time']
        if 'delivery_time' in kwargs:
            self.delivery_time = kwargs['delivery_time']


class TaskSchedulingPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to scheduling
    timepoint constraints of d-graph used for scheduling:
        start_time (TimepointConstraint): earliest and latest time for the timepoint 'start'
        pickup_time (TimepointConstraint): earliest and latest time for the timepoint 'pickup'
        delivery_time (TimepointConstraint): earliest and latest time for the timepoint 'delivery'
    """
    start_time = fields.EmbeddedDocumentField(TimepointConstraint)
    pickup_time = fields.EmbeddedDocumentField(TimepointConstraint)
    delivery_time = fields.EmbeddedDocumentField(TimepointConstraint)

    def update(self, **kwargs):
        if 'start_time' in kwargs:
            self.start_time = kwargs['start_time']
        if 'pickup_time' in kwargs:
            self.pickup_time = kwargs['pickup_time']
        if 'delivery_time' in kwargs:
            self.delivery_time = kwargs['delivery_time']


class TaskExecutionPerformance(EmbeddedMongoModel):
    """ Task performance metrics related to execution

    Assignments to timepoints:
        start_time (datetime): time assigned the timepoint 'start'
        pickup_time (datetime): time assigned to the timepoint 'pickup'
        delivery_time (datetime): time assigned to the timepoint 'delivery'

    delay (float): Time (in seconds) between latest admissible time and execution time
                  (if the execution time is later than the latest admissible time)
                   for all timepoints in the dispatchable graph


    earliness (float): Time (in seconds) between the execution time and earliest admissible
                       (if the execution time is earlier than the earliest admissible time)
                       for all timepoints in the dispatchable graph
    """

    start_time = fields.DateTimeField()
    pickup_time = fields.DateTimeField()
    delivery_time = fields.DateTimeField()
    delay = fields.FloatField(default=0.0)
    earliness = fields.FloatField(default=0.0)

    def update(self, start_time, pickup_time, delivery_time):
        self.start_time = start_time
        self.pickup_time = pickup_time
        self.delivery_time = delivery_time


class TaskPerformance(MongoModel):
    """ Stores task performance information:

    task (Task): Reference to Task object
    allocation (TaskAllocationPerformance):  Task performance metrics related to allocation
    scheduling (TaskSchedulingPerformance):  Task performance metrics related to scheduling
    execution (TaskExecutionPerformance):  Task performance metrics related to execution

    """
    task_id = fields.UUIDField(primary_key=True, required=True)
    allocation = fields.EmbeddedDocumentField(TaskAllocationPerformance)
    scheduling = fields.EmbeddedDocumentField(TaskSchedulingPerformance)
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

    def update_scheduling(self, **kwargs):
        if not self.scheduling:
            self.scheduling = TaskSchedulingPerformance()
        self.scheduling.update(**kwargs)
        self.save(cascade=True)

    def update_execution(self, start_time, pickup_time, delivery_time):
        if not self.execution:
            self.execution = TaskExecutionPerformance()
        self.execution.update(start_time, pickup_time, delivery_time)
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
