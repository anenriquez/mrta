
import logging

from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst

from mrs.dispatching.request import DispatchRequest


class Dispatcher(object):

    def __init__(self, stp_solver, timetable_manager,  **kwargs):
        self.logger = logging.getLogger('mrs.dispatcher')
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        self.stp_solver = stp_solver
        self.timetable_manager = timetable_manager

        self.re_allocate = kwargs.get('re_allocate', False)
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

    def dispatch_request_cb(self, msg):
        payload = msg['payload']
        dispatch_request = DispatchRequest.from_payload(payload)
        task = Task.get_task(dispatch_request.task_id)
        for robot_id in task.assigned_robots:
            self.dispatch_task(task, robot_id)
        task.update_status(TaskStatusConst.DISPATCHED)

    def dispatch_task(self, task, robot_id):
        """
        Sends a task to the appropriate robot in the fleet

        Args:
            task: a ropod.structs.task.Task object
            robot_id: a robot UUID
        """
        self.logger.info("Dispatching task to robot %s", robot_id)
        task_msg = self.api.create_message(task)
        self.api.publish(task_msg, peer=robot_id)



