import logging

from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst

from mrs.exceptions.execution import InconsistentSchedule
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
        self.schedule_monitor = ScheduleMonitor(robot_id,
                                                stp_solver,
                                                allocation_method,
                                                corrective_measure)
        self.queued_tasks = list()
        self.scheduled_tasks = list()
        self.ongoing_task = None
        self.logger = logging.getLogger("mrs.executor.interface.%s" % self.robot_id)
        self.logger.debug("Executor interface initialized %s", self.robot_id)

    def execute(self, task):
        self.scheduled_tasks.remove(task)
        self.ongoing_task = task
        self.logger.debug("Starting execution of task %s", task.task_id)

    def run(self):
        if self.queued_tasks:
            task = self.queued_tasks.pop(0)
            try:
                scheduled_task = self.schedule_monitor.schedule(task)
                self.scheduled_tasks.append(scheduled_task)
            except InconsistentSchedule:
                pass

        if self.scheduled_tasks and self.ongoing_task is None:
            for task in self.scheduled_tasks:
                if task.is_executable():
                    self.execute(task)

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        self.logger.debug("Received task %s", task.task_id)
        if self.robot_id in task.assigned_robots:
            self.queued_tasks.append(task)


