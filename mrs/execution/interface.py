import logging

from mrs.exceptions.execution import InconsistentSchedule
from mrs.exceptions.execution import MissingDispatchableGraph
from mrs.scheduling.monitor import ScheduleMonitor


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
        self.scheduled_tasks = list()
        self.ongoing_task = None
        self.finished_tasks = list()
        self.schedule_monitor = ScheduleMonitor(robot_id,
                                                stp_solver,
                                                allocation_method,
                                                corrective_measure,
                                                time_resolution,
                                                self.ongoing_task,
                                                self.scheduled_tasks,
                                                self.finished_tasks)
        self.queued_tasks = list()
        self.logger = logging.getLogger("mrs.executor.interface.%s" % self.robot_id)
        self.logger.debug("Executor interface initialized %s", self.robot_id)

    def execute(self, task):
        self.scheduled_tasks.remove(task)
        self.ongoing_task = task
        self.logger.debug("Starting execution of task %s", task.task_id)

    def task_progress_cb(self):
        # For now, assume that the task's timepoints get assigned their latest time
        # TODO: Receive task progress msgs
        if self.ongoing_task:
            pickup_time = self.schedule_monitor.dispatchable_graph.get_time(self.ongoing_task.task_id, 'start', False)
            self.logger.debug("Task %s, assigning pickup_time %s", self.ongoing_task.task_id, pickup_time)
            self.schedule_monitor.assign_timepoint(pickup_time, self.ongoing_task.task_id, 'start')

            delivery_time = self.schedule_monitor.dispatchable_graph.get_time(self.ongoing_task.task_id, 'finish', False)
            self.logger.debug("Task %s, assigning delivery_time %s", self.ongoing_task.task_id, delivery_time)
            self.schedule_monitor.assign_timepoint(delivery_time, self.ongoing_task.task_id, 'finish')

            self.finished_tasks.append(self.ongoing_task)
            self.ongoing_task = None

    def run(self):
        if self.queued_tasks:
            task = self.queued_tasks.pop(0)
            try:
                scheduled_task = self.schedule_monitor.schedule(task)
                self.scheduled_tasks.append(scheduled_task)
            except MissingDispatchableGraph:
                pass
            except InconsistentSchedule:
                pass

        if self.scheduled_tasks and self.ongoing_task is None:
            for task in self.scheduled_tasks:
                if task.is_executable():
                    self.execute(task)

        self.task_progress_cb()


