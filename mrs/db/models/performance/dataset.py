import logging

from pymodm import fields, MongoModel
from pymodm.context_managers import switch_collection
from pymodm.context_managers import switch_connection
from pymongo.errors import ServerSelectionTimeoutError
from ropod.utils.uuid import generate_uuid

from mrs.db.models.performance.task import TaskPerformance


class DatasetPerformance(MongoModel):
    """ Stores dataset performance information:

    dataset_id (UUID):  uniquely identifies the dataset

    completion_time (float):    Difference between the start navigation of the
                                first task and the finish time of the last allocated
                                task
    makespan (float):   Finish time of the last allocated task

    fleet_work_time (float):  % of time taken to perform all allocated tasks.

    fleet_travel_time (float): % of time taken to travel to task locations

    fleet_idle_time (float): % of time robots are idle (waiting) to start their next allocated task

    robot_usage (float): % of robots used out of all the available robots

    usage_most_loaded_robot (float): % of tasks allocated to the robot with most allocations

    """
    dataset_id = fields.UUIDField(primary_key=True, default=generate_uuid())
    completion_time = fields.FloatField()
    makespan = fields.FloatField()
    fleet_work_time = fields.FloatField()
    fleet_travel_time = fields.FloatField()
    fleet_idle_time = fields.FloatField()
    robot_usage = fields.FloatField()
    usage_most_loaded_robot = fields.FloatField()
    tasks = fields.ListField(fields.ReferenceField(TaskPerformance))

    class Meta:
        archive_collection = 'dataset_performance_archive'
        ignore_unknown_fields = True

    def archive(self):
        with switch_collection(DatasetPerformance, DatasetPerformance.Meta.archive_collection):
            super().save()
        self.delete()

