import argparse
import logging.config
import time

from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst

from mrs.config.configurator import Configurator
from mrs.db.models.task import TaskLot


class Robot:
    def __init__(self, robot_id, bidder, **kwargs):
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)

        self.robot_id = robot_id
        self.api = components.get('api')
        self.robot_store = components.get('robot_store')
        self.bidder = bidder
        self.executor_interface = kwargs.get('executor_interface')

        self.api.register_callbacks(self)

        self.logger.info("Initialized Robot %s", robot_id)

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        self.logger.debug("Received task %s", task.task_id)
        if self.robot_id in task.assigned_robots:
            task.update_status(TaskStatusConst.DISPATCHED)
            self.executor_interface.tasks.append(task)
            TaskLot.freeze_task(task.task_id)

    def run(self):
        try:
            self.api.start()
            while True:
                self.executor_interface.run()
                # Provisional hack
                if self.executor_interface.task_to_archive:
                    self.bidder.archive_task(self.executor_interface.task_to_archive.robot_id,
                                             self.executor_interface.task_to_archive.task_id,
                                             self.executor_interface.task_to_archive.node_id)
                    self.executor_interface.task_to_archive = None
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.robot_id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('robot_id', type=str, help='example: ropod_001')
    args = parser.parse_args()

    config = Configurator(args.file)
    components = config.config_robot(args.robot_id)

    robot = Robot(**components)
    robot.run()
