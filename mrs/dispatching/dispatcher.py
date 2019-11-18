
import logging
from datetime import timedelta

from ropod.structs.task import TaskStatus as TaskStatusConst
from ropod.utils.timestamp import TimeStamp


class Dispatcher(object):

    def __init__(self, stp_solver, timetable_manager, freeze_window, **kwargs):
        self.logger = logging.getLogger('mrs.dispatcher')
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        self.stp_solver = stp_solver
        self.timetable_manager = timetable_manager
        self.freeze_window = timedelta(seconds=freeze_window)

        self.robot_ids = list()

        self.logger.debug("Dispatcher started")

    def configure(self, **kwargs):
        api = kwargs.get('api')
        ccu_store = kwargs.get('ccu_store')
        if api:
            self.api = api
        if ccu_store:
            self.ccu_store = ccu_store

    def register_robot(self, robot_id):
        self.logger.debug("Registering robot %s", robot_id)
        self.robot_ids.append(robot_id)

    def dispatch_tasks(self):
        for robot_id in self.robot_ids:
            timetable = self.timetable_manager.get_timetable(robot_id)
            tasks = timetable.get_earliest_tasks()
            for task in tasks:
                if task.status.status == TaskStatusConst.PLANNED:
                    start_time = timetable.get_start_time(task.task_id)
                    if self.is_schedulable(start_time):
                        self.dispatch_task(task, robot_id)

    def is_schedulable(self, start_time):
        current_time = TimeStamp()
        if start_time.get_difference(current_time) < self.freeze_window:
            return True
        return False

    def dispatch_task(self, task, robot_id):
        """
        Sends a task to the appropriate robot in the fleet

        Args:
            task: a ropod.structs.task.Task object
            robot_id: a robot UUID
        """
        self.logger.critical("Dispatching task to robot %s", robot_id)
        task_msg = self.api.create_message(task)
        self.api.publish(task_msg, peer=robot_id)
        task.update_status(TaskStatusConst.DISPATCHED)



