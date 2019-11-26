import logging

from mrs.exceptions.execution import InconsistentSchedule
from mrs.exceptions.execution import MissingDispatchableGraph
from mrs.scheduling.monitor import ScheduleMonitor
from ropod.structs.task import TaskStatus as TaskStatusConst
from mrs.execution.archive_task import ArchiveTask


class ExecutorInterface:
    def __init__(self, robot_id,
                 stp_solver,
                 allocation_method,
                 corrective_measure,
                 **kwargs):
        self.robot_id = robot_id
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')
        time_resolution = kwargs.get('time_resolution', 0.5)
        self.tasks = list()
        self.archived_tasks = list()
        self.task_to_archive = None
        self.schedule_monitor = ScheduleMonitor(robot_id,
                                                stp_solver,
                                                allocation_method,
                                                corrective_measure,
                                                time_resolution,
                                                self.tasks)
        self.logger = logging.getLogger("mrs.executor.interface.%s" % self.robot_id)
        self.logger.debug("Executor interface initialized %s", self.robot_id)

    def execute(self, task):
        self.logger.debug("Starting execution of task %s", task.task_id)

    def task_progress_cb(self):
        # For now, assume that the task's timepoints get assigned their latest time
        # TODO: Receive task progress msgs
        for task in self.tasks:
            if task.status.status == TaskStatusConst.ONGOING:
                pickup_time = self.schedule_monitor.dispatchable_graph.get_time(task.task_id, 'start', False)
                self.logger.debug("Task %s, assigning pickup_time %s", task.task_id, pickup_time)
                self.schedule_monitor.assign_timepoint(pickup_time, task.task_id, 'start')

                delivery_time = self.schedule_monitor.dispatchable_graph.get_time(task.task_id, 'finish', False)
                self.logger.debug("Task %s, assigning delivery_time %s", task.task_id, delivery_time)
                self.schedule_monitor.assign_timepoint(delivery_time, task.task_id, 'finish')

                self.archive_task(task)

    def archive_task(self, task):
        self.logger.debug("Deleting task: %s", task.task_id)
        task.update_status(TaskStatusConst.COMPLETED)
        self.tasks.remove(task)
        self.archived_tasks.append(task)
        node_id = self.schedule_monitor.remove_task(task.task_id)
        archive_task = ArchiveTask(self.robot_id, task.task_id, node_id)
        # Provisional hack
        self.task_to_archive = archive_task
        archive_task_msg = self.api.create_message(archive_task)
        self.api.publish(archive_task_msg)

    def run(self):
        for task in self.tasks:
            if task.status.status == TaskStatusConst.DISPATCHED:
                try:
                    scheduled_task = self.schedule_monitor.schedule(task)
                    scheduled_task.update_status(TaskStatusConst.SCHEDULED)
                except MissingDispatchableGraph:
                    pass
                except InconsistentSchedule:
                    pass

            if task.status.status == TaskStatusConst.SCHEDULED and task.is_executable():
                task.update_status(TaskStatusConst.ONGOING)
                self.execute(task)

        self.task_progress_cb()


