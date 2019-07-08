from allocation.auctioneer import Auctioneer
from allocation.config.loader import Config
from datasets.dataset_loader import load_dataset
import time
import logging
from allocation.utils.config_logger import config_logger


class TaskAllocator(object):
    def __init__(self, auctioneer_config):
        self.logger = logging.getLogger('allocation.task_allocator')
        self.auctioneer = Auctioneer(**auctioneer_config)
        self.allocated_tasks = dict()

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

            self.auctioneer.allocate_next_task = True
            self.auctioneer.allocation_completed = False

    def run(self):
        try:
            while True:
                self.auctioneer.run()
                self.get_allocation()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            print("Terminating test")
            self.auctioneer.shutdown()


if __name__ == '__main__':

    config = Config("../config/config.yaml")
    auctioneer_config = config.configure_auctioneer()
    config_logger('../config/logging.yaml')
    logging.info("Starting Task Allocator")
    test = TaskAllocator(auctioneer_config)

    tasks = load_dataset('three_tasks.csv')
    test.get_robots_for_task(tasks)
    test.run()