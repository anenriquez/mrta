import argparse
import logging.config
import time

from mrs.config.configurator import Configurator
from mrs.db.models.task import EstimatedDuration
from mrs.db.models.task import TransportationTask as Task
from mrs.messages.archive_task import ArchiveTask
from ropod.structs.task import TaskStatus as TaskStatusConst


class CCU:
    def __init__(self, config_file=None):
        self.logger = logging.getLogger('mrs.ccu')
        self.logger.info("Configuring CCU...")

        config = Configurator(config_file)
        components = config.config_ccu()

        self.auctioneer = components.get('auctioneer')
        self.dispatcher = components.get('dispatcher')
        self.planner = components.get('planner')
        self.api = components.get('api')
        self.ccu_store = components.get('ccu_store')

        self.api.register_callbacks(self)
        self.logger.info("Initialized CCU")

        self.unallocated_tasks = dict()

    def start_test_cb(self, msg):
        self.logger.debug("Start test msg received")
        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        for task in tasks:
            plan = self.get_task_plan(task)
            self.unallocated_tasks[task.task_id] = {'task': task,
                                                    'plan': plan}
            work_time = self.get_plan_work_time(plan)
            task.update_work_time(work_time)

        self.auctioneer.allocate(tasks)

    def get_task_plan(self, task):
        return self.planner.get_path(task.request.pickup_location, task.request.delivery_location)

    def get_plan_work_time(self, plan):
        mean, variance = self.planner.get_estimated_duration(plan)
        work_time = EstimatedDuration(mean=mean, variance=variance)
        return work_time

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


