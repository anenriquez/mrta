import time
import logging

from fleet_management.config.loader import Config
from mrs.utils.datasets import load_yaml_dataset
from mrs.timetable import Timetable


class TaskAllocator(object):
    def __init__(self, config_file=None):
        self.logger = logging.getLogger('test')

        config = Config(config_file, initialize=True)
        config.configure_logger()
        self.ccu_store = config.ccu_store

        self.auctioneer = config.configure_task_allocator(self.ccu_store)
        # self.auctioneer.register_api_callbacks()

        self.allocated_tasks = dict()
        self.test_terminated = False
        self.allocations = list()
        self.reset_timetables()

    def reset_timetables(self):
        self.logger.debug("Resetting timetables")

        for robot_id in self.auctioneer.robot_ids:
            timetable = Timetable(self.auctioneer.stp, robot_id)
            self.ccu_store.update_timetable(timetable)

    def get_robots_for_task(self, tasks):
        """ Adds a task or list of tasks to the list of tasks_to_allocate
        in the auctioneer

        :param tasks: list of tasks to allocate
        """
        self.auctioneer.allocate(tasks)

    def get_allocation(self):
        """ Gets the allocation of a task when the auctioneer terminates an
         allocation round
        """

        while self.auctioneer.allocations:
            allocation = self.auctioneer.allocations.pop()
            self.logger.debug("Allocation %s: ", allocation)
            self.allocations.append(allocation)

    def check_test_termination(self):
        if not self.auctioneer.tasks_to_allocate:
            self.test_terminated = True
            self.logger.debug("Allocations %s", self.allocations)
            self.reset_timetables()

    def run(self):
        timeout_duration = 300  # 5 minutes
        try:
            self.auctioneer.api.start()
            start_time = time.time()
            while not self.test_terminated and start_time + timeout_duration > time.time():
                self.auctioneer.api.run()
                self.auctioneer.run()
                self.get_allocation()
                self.check_test_termination()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            print("Test interrupted")

        print("Terminating test")
        self.auctioneer.api.shutdown()


if __name__ == '__main__':

    tasks = load_yaml_dataset('data/non_overlapping_1.yaml')
    config_file_path = '../config/config.yaml'

    for task in tasks:
        print(task.id)

    test = TaskAllocator(config_file_path)
    time.sleep(5)

    test.get_robots_for_task(tasks)
    test.run()
