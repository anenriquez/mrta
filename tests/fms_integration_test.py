import time
import logging

from fleet_management.config.loader import Config
from mrs.utils.datasets import load_yaml_dataset
from mrs.structs.timetable import Timetable
from mrs.db_interface import DBInterface
from ropod.pyre_communicator.base_class import RopodPyre


class TaskAllocator(RopodPyre):
    def __init__(self, config_file=None):
        zyre_config = {'node_name': 'task_request_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['TASK', 'ALLOCATION']}
        super().__init__(zyre_config, acknowledge=False)

        self.logger = logging.getLogger('test')

        config = Config(config_file, initialize=True)
        config.configure_logger()
        ccu_store = config.ccu_store
        self.db_interface = DBInterface(ccu_store)
        self.auctioneer = config.configure_auctioneer(ccu_store)
        self.auctioneer.api.register_callbacks(self.auctioneer)

        self.allocated_tasks = dict()
        self.test_terminated = False
        self.allocations = list()
        self.reset_timetables()

    def reset_timetables(self):
        self.logger.debug("Resetting timetables")

        for robot_id in self.auctioneer.robot_ids:
            timetable = Timetable(self.auctioneer.stp, robot_id)
            self.db_interface.update_timetable(timetable)
            self.send_timetable(timetable, robot_id)

    def reset_tasks(self):
        self.logger.info("Resetting tasks")
        tasks_dict = self.db_interface.get_tasks()
        for task_id, task_info in tasks_dict.items():
            self.db_interface.remove_task(task_id)

    def send_timetable(self, timetable, robot_id):
        self.logger.debug("Sending timetable to %s", robot_id)
        timetable_msg = dict()
        timetable_msg['header'] = dict()
        timetable_msg['payload'] = dict()
        timetable_msg['header']['type'] = 'TIMETABLE'
        timetable_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        timetable_msg['header']['msgId'] = generate_uuid()
        timetable_msg['header']['timestamp'] = ts.get_time_stamp()

        timetable_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'
        timetable_msg['payload']['timetable'] = timetable.to_dict()
        self.shout(timetable_msg)

    def get_robots_for_task(self, tasks):
        """ Adds a task or list of tasks to the list of tasks_to_allocate
        in the auctioneer_name

        :param tasks: list of tasks to allocate
        """
        self.auctioneer.allocate(tasks)

    def get_allocation(self):
        """ Gets the allocation of a task when the auctioneer_name terminates an
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
            self.reset_timetables()
            self.reset_tasks()
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
