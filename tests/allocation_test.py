import time
import logging

from fleet_management.config.loader import Config
from allocation.utils.datasets import load_yaml_dataset


class TaskAllocator(object):
    def __init__(self, config_file=None):
        self.logger = logging.getLogger('test')

        config = Config(config_file, initialize=True)
        config.configure_logger()

        self.auctioneer = config.configure_task_allocator()
        self.register_api_callbacks(config.api)

        self.allocated_tasks = dict()
        self.test_terminated = False
        self.allocations = list()

    def register_api_callbacks(self, api):
        for option in api.middleware_collection:
            option_config = api.config_params.get(option, None)
            if option_config is None:
                self.logger.warning("Option %s has no configuration", option)
                continue

            callbacks = option_config.get('callbacks', list())
            for callback in callbacks:
                component = callback.pop('component', None)
                function = self.__get_callback_function(component)
                api.register_callback(option, function, **callback)

    def __get_callback_function(self, component):
        objects = component.split('.')
        child = objects.pop(0)
        parent = getattr(self, child)
        while objects:
            child = objects.pop(0)
            parent = getattr(parent, child)

        return parent

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
            print(allocation)
            # self.logger.debug("Allocation %s: ", allocation)
            self.allocations.append(allocation)

    def check_test_termination(self):
        if not self.auctioneer.tasks_to_allocate:
            self.test_terminated = True
            # self.logger.debug("Allocations %s", self.allocations)

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
