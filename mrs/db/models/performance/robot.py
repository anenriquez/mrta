from fmlib.models.robot import RobotManager as RobotPerformanceManager
from pymodm import fields, MongoModel

from mrs.db.models.timetable import Timetable


class RobotPerformance(MongoModel):
    """ Stores robot performance information:
    Metrics are computed based on the completed tasks

    robot_id (str):  Identifies the robot

    total_time (float): Difference between the start of the first task and the finish time of the last task

    makespan (datetime): Finish time of the last task

    travel_time (float): Time taken to travel to task locations

    work_time (float):  Time taken to perform all allocated tasks.

    idle_time (float): Time robots are idle (waiting) to start their next allocated task

    """
    robot_id = fields.CharField(primary_key=True)
    allocated_tasks = fields.ListField()
    total_time = fields.FloatField(default=0.0)
    makespan = fields.DateTimeField()
    travel_time = fields.FloatField(default=0.0)
    work_time = fields.FloatField(default=0.0)
    idle_time = fields.FloatField(default=0.0)
    timetables = fields.EmbeddedDocumentListField(Timetable)

    objects = RobotPerformanceManager()

    class Meta:
        ignore_unknown_fields = True

    @classmethod
    def create_new(cls, robot_id):
        performance = cls(robot_id=robot_id)
        performance.save()
        return performance

    def update_allocated_tasks(self, task_id):
        if not self.allocated_tasks:
            self.allocated_tasks = list()
        if task_id not in self.allocated_tasks:
            self.allocated_tasks.append(task_id)
        self.save()

    def unallocated(self, task_id):
        self.allocated_tasks.remove(task_id)
        self.save()

    def update_travel_time(self, travel_time):
        self.travel_time += travel_time
        self.save()

    def update_work_time(self, work_time):
        self.work_time += work_time
        self.save()

    def update_idle_time(self, idle_time):
        self.idle_time += idle_time
        self.save()

    def update_total_time(self, total_time):
        self.total_time = total_time
        self.save()

    def update_timetables(self, timetable):
        if not self.timetables:
            self.timetables = list()
        timetable_model = timetable.to_model()
        self.timetables.append(timetable_model)
        self.save()

    def update_makespan(self, makespan):
        self.makespan = makespan
        self.save()

    @classmethod
    def get_robot_performance(cls, robot_id):
        return cls.objects.get_robot(robot_id)
