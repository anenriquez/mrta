import collections
import logging

from fmlib.models.tasks import TaskStatus
from fmlib.models.tasks import TransportationTask as Task
from mrs.performance.robot import RobotPerformanceTracker
from mrs.performance.task import TaskPerformanceTracker
from pymodm.context_managers import switch_collection
from ropod.structs.status import TaskStatus as TaskStatusConst


class PerformanceTracker:
    def __init__(self, auctioneer, timetable_monitor, **kwargs):
        self.auctioneer = auctioneer
        self.timetable_manager = auctioneer.timetable_manager
        self.timetable_monitor = timetable_monitor

        self.task_performance_tracker = TaskPerformanceTracker()
        self.robot_performance_tracker = RobotPerformanceTracker()

        self.logger = logging.getLogger("mrs.performance.tracker")

    def update_allocation_metrics(self, task, allocation_time=None, only_constraints=False):
        for robot_id in task.assigned_robots:
            timetable = self.timetable_manager.get_timetable(robot_id)
            self.task_performance_tracker.update_allocation_metrics(task.task_id, timetable, allocation_time, only_constraints)
            self.robot_performance_tracker.update_allocated_tasks(robot_id, task.task_id)
            self.update_timetables(timetable)

    def update_timetables(self, timetable):
        self.robot_performance_tracker.update_timetables(timetable)

    def update_scheduling_metrics(self, task_id, timetable):
        self.task_performance_tracker.update_scheduling_metrics(task_id, timetable)

    def update_delay(self, task_id, assigned_time, node_type, timetable):
        self.task_performance_tracker.update_delay(task_id, assigned_time, node_type, timetable)

    def update_earliness(self, task_id, assigned_time, node_type, timetable):
        self.task_performance_tracker.update_earliness(task_id, assigned_time, node_type, timetable)

    @staticmethod
    def get_tasks_status(robot_id):
        tasks_status = collections.OrderedDict()
        with switch_collection(Task, Task.Meta.archive_collection):
            tasks = Task.get_tasks_by_robot(robot_id)
        with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
            for task in tasks:
                task_status = TaskStatus.objects.get({"_id": task.task_id})
                if task_status.status == TaskStatusConst.COMPLETED:
                    tasks_status[task.task_id] = task_status
        return tasks_status

    def run(self):
        while self.timetable_monitor.completed_tasks:
            task = self.timetable_monitor.completed_tasks[0]
            self.task_performance_tracker.update_execution_metrics(task)

            for robot_id in task.assigned_robots:
                tasks_status = self.get_tasks_status(robot_id)
                self.robot_performance_tracker.update_metrics(robot_id, tasks_status)

            self.timetable_monitor.completed_tasks.pop(0)

        while self.timetable_monitor.tasks_to_reallocate:
            task = self.timetable_monitor.tasks_to_reallocate.pop(0)
            self.task_performance_tracker.update_re_allocations(task)
            self.robot_performance_tracker.update_re_allocations(task)
