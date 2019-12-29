import argparse
import logging.config
import time

from fmlib.models.robot import Robot as RobotModel
from ropod.structs.task import TaskStatus as TaskStatusConst

from mrs.config.configurator import Configurator
from mrs.db.models.task import Task


class Robot:
    def __init__(self, robot_id, api, robot_store, bidder, **kwargs):
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)

        self.robot_id = robot_id
        self.api = api
        self.robot_store = robot_store
        self.bidder = bidder
        self.executor_interface = kwargs.get('executor_interface')
        self.robot_model = RobotModel.create_new(robot_id)

        self.api.register_callbacks(self)
        self.logger.info("Initialized Robot %s", robot_id)

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        self.logger.debug("Received task %s", task.task_id)
        if self.robot_id in task.assigned_robots:
            task.update_status(TaskStatusConst.DISPATCHED)
            self.executor_interface.tasks.append(task)
            Task.freeze_task(task.task_id)

    def robot_pose_cb(self, msg):
        payload = msg.get("payload")
        self.logger.debug("Robot %s received pose", self.robot_id)
        self.robot_model.update_position(**payload.get("pose"))

    def run(self):
        try:
            self.api.start()
            while True:
                self.executor_interface.run()
                # Provisional hack
                if self.executor_interface.task_to_archive:
                    self.bidder.archive_task(self.executor_interface.task_to_archive)
                    self.executor_interface.task_to_archive = None
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
    components = config.config_robot(args.robot_id)

    robot = Robot(**components)
    robot.run()
