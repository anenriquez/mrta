import logging
from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst


class ExecutorInterface:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.logger = logging.getLogger("mrs.executor.interface")
        self.logger.debug("Executor interface initialized %s", self.robot_id)

    def execute(self, task_id):
        self.logger.debug("Starting execution of task %s", task_id)
        task = Task.get_task(task_id)
        task.update_status(TaskStatusConst.ONGOING)

