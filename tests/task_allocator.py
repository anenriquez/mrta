from allocation.auctioneer import Auctioneer
from allocation.config.loader import Config
from datasets.dataset_loader import load_dataset
import time
import logging
import argparse
from allocation.utils.config_logger import config_logger


class TaskAllocator(object):
    def __init__(self, auctioneer_config):
        self.logger = logging.getLogger('allocation.task_allocator')
        self.auctioneer = Auctioneer(**auctioneer_config)
        self.allocated_tasks = dict()
        self.test_terminated = False

    ''' Adds a task or list of tasks to the list of tasks_to_allocate in the auctioneer
    '''
    def get_robots_for_task(self, tasks):
        self.auctioneer.allocate(tasks)

    ''' Gets the allocation of a task when the auctioneer terminates an allocation round
    '''
    def get_allocation(self):

        if self.auctioneer.allocation_completed:

            allocation = self.auctioneer.get_allocation(self.auctioneer.allocated_task)

            self.logger.debug("Allocation %s: ", allocation)

            self.auctioneer.allocate_next()

    def check_test_termination(self):
        if not self.auctioneer.tasks_to_allocate and self.auctioneer.allocate_next_task:
            self.test_terminated = True

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

    parser = argparse.ArgumentParser()
    parser.add_argument('dataset_name', type=str,
                        choices=['three_tasks.csv',
                                 'overlapping_tasks.csv'])
    args = parser.parse_args()
    dataset_name = args.dataset_name

    config = Config("../config/config.yaml")
    auctioneer_config = config.configure_auctioneer()
    config_logger('../config/logging.yaml')

    logging.info("Starting Task Allocator")
    test = TaskAllocator(auctioneer_config)

    tasks = load_dataset(dataset_name)
    test.get_robots_for_task(tasks)
    test.run()
