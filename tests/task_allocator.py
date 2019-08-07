from allocation.config.loader import Config
import time
import logging
from allocation.utils.config_logger import config_logger
from allocation.utils.datasets import load_yaml_dataset


class TaskAllocator(object):
    def __init__(self, auctioneer):
        self.logger = logging.getLogger('allocation.task_allocator')
        self.auctioneer = auctioneer
        self.allocated_tasks = dict()
        self.test_terminated = False
        self.allocations = list()

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

    def run(self):
        timeout_duration = 300  # 5 minutes
        try:
            start_time = time.time()
            while not self.test_terminated and start_time + timeout_duration > time.time():
                self.auctioneer.run()
                self.get_allocation()
                self.check_test_termination()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            print("Test interrupted")

        print("Terminating test")
        self.auctioneer.shutdown()


if __name__ == '__main__':

    tasks = load_yaml_dataset('data/non_overlapping_1.yaml')

    for task in tasks:
        print(task.id)

    config = Config("../config/config.yaml")
    auctioneer = config.configure_auctioneer()

    config_logger('../config/logging.yaml')

    logging.info("Starting Task Allocator")
    test = TaskAllocator(auctioneer)

    test.get_robots_for_task(tasks)
    test.run()
