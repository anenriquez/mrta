import logging
from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst
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
        self.task_queue = None
        self.logger = logging.getLogger("mrs.executor.interface.%s" % self.robot_id)
        self.logger.debug("Executor interface initialized %s", self.robot_id)

    def execute(self, task_id):
        self.logger.debug("Starting execution of task %s", task_id)
        task = Task.get_task(task_id)
        task.update_status(TaskStatusConst.ONGOING)

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        task.update_status(TaskStatusConst.DISPATCHED)
        self.logger.critical("Received task %s", task.task_id)
        # TODO: Add in task.queue

