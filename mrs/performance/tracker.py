import logging

from fmlib.models.tasks import TaskStatus
from mrs.db.models.task import Task
from mrs.messages.recover import ReAllocate
from mrs.performance.robot import RobotPerformanceTracker
from mrs.performance.task import TaskPerformanceTracker
from pymodm.context_managers import switch_collection


class PerformanceTracker:
    def __init__(self, auctioneer, timetable_manager, timetable_monitor, **kwargs):
        self.auctioneer = auctioneer
        self.timetable_manager = timetable_manager
        self.timetable_monitor = timetable_monitor

        self.task_performance_tracker = TaskPerformanceTracker(auctioneer)
        self.robot_performance_tracker = RobotPerformanceTracker()

        self.logger = logging.getLogger("mrs.performance.tracker")

    def re_allocate_cb(self, msg):
        payload = msg['payload']
        recover = ReAllocate.from_payload(payload)
        self.task_performance_tracker.update_re_allocations(recover.task_id)

    def update_task_allocation_metrics(self, allocated_task_id, robot_ids, tasks_to_update):
        for robot_id in robot_ids:
            timetable = self.timetable_manager.get_timetable(robot_id)
            self.task_performance_tracker.update_allocation_metrics(allocated_task_id, timetable, tasks_to_update)

    @staticmethod
    def get_tasks_progress(robot_id):
        tasks_progress = list()
        with switch_collection(Task, Task.Meta.archive_collection):
            with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
                tasks = Task.get_tasks_by_robot(robot_id)
                for task in tasks:
                    task_status = TaskStatus.objects.get({"_id": task.task_id})
                    tasks_progress.append(task_status.progress.actions)
        return tasks_progress

    def run(self):
        while self.timetable_monitor.completed_tasks:
            task = self.timetable_monitor.completed_tasks.pop(0)
            self.task_performance_tracker.update_execution_metrics(task)

            for robot_id in task.assigned_robots:
                tasks_progress = self.get_tasks_progress(robot_id)
                self.robot_performance_tracker.update_metrics(robot_id, tasks_progress)
