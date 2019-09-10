import logging

from mrs.db_interface import DBInterface
from mrs.models.task import TaskStatus


class TaskMonitor(object):
    def __init__(self, ccu_store, task_cls, api):
        self.db_interface = DBInterface(ccu_store)
        self.task_cls = task_cls
        self.api = api

    def run(self):
        pass

    def task_progress_cb(self, msg):
        task_id = msg["payload"]["taskId"]
        robot_id = msg["payload"]["robotId"]
        task_status = msg["payload"]["status"]["taskStatus"]

        logging.debug("Robot %s received TASK-PROGRESS msg of task %s from %s ", task_id, robot_id)

        task_dict = self.db_interface.get_task(task_id)
        task = self.task_cls.from_dict(task_dict)

        if task_status == TaskStatus.COMPLETED or \
            task_status == TaskStatus.CANCELED or \
            task_status == TaskStatus.FAILED or \
            task_status == TaskStatus.PREEMPTED:
            self.archieve_task(task)

        elif task_status == TaskStatus.ONGOING:
            self.check_execution_progress(task)

    def archieve_task(self, task):
        # TODO: Update timetable
        pass

    def check_execution_progress(self, task):
        # TODO: check schedule consistency
        pass

