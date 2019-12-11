from fmlib.models.tasks import Task
from pymodm import EmbeddedMongoModel, fields
from fmlib.utils.messages import Document
from ropod.structs.status import TaskStatus as TaskStatusConst
from fmlib.models.tasks import TaskConstraints, TimepointConstraints


class EstimatedDuration(EmbeddedMongoModel):
    mean = fields.FloatField()
    variance = fields.FloatField()


class TransportationTask(Task):
    work_time = fields.EmbeddedDocumentField(EstimatedDuration, default=EstimatedDuration(1, 0))
    travel_time = fields.EmbeddedDocumentField(EstimatedDuration)

    def update_work_time(self, work_time):
        self.work_time = work_time
        self.save()

    @classmethod
    def from_task(cls, task):
        # TODO: Add constraints to task in Task.from_request
        pickup_constraints = TimepointConstraints(earliest_time=task.request.earliest_pickup_time,
                                                  latest_time=task.request.latest_pickup_time)
        constraints = TaskConstraints(timepoint_constraints=[pickup_constraints],
                                      hard=task.request.hard_constraints)
        return cls.create_new(task_id=task.task_id,
                              request=task.request,
                              constraints=constraints)

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        document['_id'] = document.pop('task_id')
        task = cls.from_document(document)
        task.save()
        task.update_status(TaskStatusConst.UNALLOCATED)
        return task
