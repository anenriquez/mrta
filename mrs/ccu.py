import argparse
import logging.config
import time

from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst

from mrs.config.configurator import Configurator
from mrs.messages.archive_task import ArchiveTask


class CCU:
    def __init__(self, config_file=None):
        self.logger = logging.getLogger('ccu')
        self.logger.info("Configuring CCU...")

        config = Configurator(config_file)
        components = config.config_ccu()

        self.auctioneer = components.get('auctioneer')
        self.dispatcher = components.get('dispatcher')
        self.api = components.get('api')
        self.ccu_store = components.get('ccu_store')

        self.api.register_callbacks(self)
        self.logger.info("Initialized CCU")

    def start_test_cb(self, msg):
        self.logger.debug("Start test msg received")
        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        self.auctioneer.allocate(tasks)

    def archive_task_cb(self, msg):
        payload = msg['payload']
        archive_task = ArchiveTask.from_payload(payload)
        self.auctioneer.archive_task(archive_task.robot_id, archive_task.task_id, archive_task.node_id)
        self.dispatcher.timetable_manager.send_update_to = archive_task.robot_id

    def run(self):
        try:
            self.api.start()

            while True:
                self.auctioneer.run()
                self.dispatcher.run()
                self.api.run()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.api.shutdown()
            self.logger.info('FMS is shutting down')

    def shutdown(self):
        self.api.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')

    args = parser.parse_args()
    ccu = CCU(args.file)
    ccu.run()


