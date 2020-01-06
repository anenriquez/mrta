import argparse
import logging.config
import time

from fmlib.models.robot import Robot as RobotModel
from mrs.config.configurator import Configurator
from mrs.db.models.task import Task
from mrs.messages.task_status import TaskStatus, ReAllocate
from ropod.structs.task import TaskStatus as TaskStatusConst


class RobotProxy:
    def __init__(self, robot_id, api, robot_proxy_store, bidder, **kwargs):
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)

        self.robot_id = robot_id
        self.api = api
        self.robot_proxy_store = robot_proxy_store
        self.bidder = bidder
        self.robot_model = RobotModel.create_new(robot_id)

        self.api.register_callbacks(self)
        self.logger.info("Initialized Robot %s", robot_id)

    def task_status_cb(self, msg):
        payload = msg['payload']
        task_status = TaskStatus.from_payload(payload)
        self.logger.debug("Received task status msg for task %s ", task_status.task_id)

        if task_status.status in [TaskStatusConst.COMPLETED, TaskStatusConst.CANCELED, TaskStatusConst.ABORTED]:
            self.bidder.archive_task(task_status.task_id)

        task = Task.get_task(task_status.task_id)
        task.update_status(task_status.status)

    def re_allocate_cb(self, msg):
        payload = msg['payload']
        re_allocate = ReAllocate.from_payload(payload)
        self.logger.info("Triggering reallocation of task %s robot %s", re_allocate.task_id, re_allocate.robot_id)

        self.bidder.archive_task(re_allocate.task_id)
        task = Task.get_task(re_allocate.task_id)
        task.update_status(TaskStatusConst.UNALLOCATED)

    def robot_pose_cb(self, msg):
        payload = msg.get("payload")
        self.logger.debug("Robot %s received pose", self.robot_id)
        self.robot_model.update_position(**payload.get("pose"))

    def run(self):
        try:
            self.api.start()
            while True:
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.robot_id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    args = parser.parse_args()

    config = Configurator(args.file)
    components = config.config_robot_proxy(args.robot_id)

    robot = RobotProxy(**components)
    robot.run()