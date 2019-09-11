import logging

from mrs.db.models.performance.task import TaskPerformance
from pymodm import fields, MongoModel
from pymodm.context_managers import switch_collection
from pymongo.errors import ServerSelectionTimeoutError
from ropod.utils.uuid import generate_uuid


class DatasetPerformance(MongoModel):
    """ Stores dataset performance information:

    dataset_id (UUID):  uniquely identifies the dataset

    completion_time (float):    Difference between the start navigation of the
                                first task and the finish time of the last allocated
                                task
    makespan (float):   Finish time of the last allocated task

    execution_time (float): Time taken to execute all allocated tasks.  Includes the idle
                            times between tasks.
                            idle time: time between the finish time of the last task and
                            the start navigation time of the next task. The first task in
                            a robot's schedule has no idle time.


    work_time_percentage (float):  % of time from the execution_time taken to perform
                                    all allocated tasks.

    travel_time_percentage (float): % of time from the execution_time, taken to travel
                                    to the task location

    idle_time_percentage (float): % of time from the execution_time that the robot is
                                    waiting (idle) to start its next allocated task

    robot_usage (float): % of robots used out of all the available robots

    usage_most_loaded_robot (float): % of tasks allocated tot the robot with most allocations

    """
    dataset_id = fields.UUIDField(primary_key=True, default=generate_uuid())
    completion_time = fields.FloatField()
    makespan = fields.FloatField()
    execution_time = fields.FloatField()
    work_time_percentage = fields.FloatField()
    travel_time_percentage = fields.FloatField()
    idle_time_percentage = fields.FloatField()
    robot_usage = fields.FloatField()
    usage_most_loaded_robot = fields.FloatField()
    tasks = fields.ListField(fields.ReferenceField(TaskPerformance))

    class Meta:
        archive_collection = 'dataset_performance_archive'
        ignore_unknown_fields = True

    def save(self):
        try:
            super().save(cascade=True)
        except ServerSelectionTimeoutError:
            logging.warning('Could not save models to MongoDB')

    def archive(self):
        with switch_collection(DatasetPerformance, DatasetPerformance.Meta.archive_collection):
            super().save()
        self.delete()

    @classmethod
    def create(cls, dataset_id, task_ids):
        performance = cls(dataset_id=dataset_id, tasks=task_ids)
        performance.save()
        return performance
