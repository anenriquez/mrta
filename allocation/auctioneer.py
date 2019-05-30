from temporal.structs.area import Area
from temporal.structs.task import Task
import uuid
import time
import datetime
import collections
import logging
import logging.config
import os
import yaml
from ropod.pyre_communicator.base_class import RopodPyre
from allocation.config.config_file_reader import ConfigFileReader
SLEEP_TIME = 0.350

'''  Implements the TeSSI algorithm with different bidding rules:

    - Rule 1: Lowest completion time (last task finish time - first task start time)
    - Rule 2: Lowest combination of completion time and travel distance_robot
    - Rule 3: Lowest makespan (finish time of the last task in the schedule)
    - Rule 4: Lowest combination of makespan and travel distance_robot
    - Rule 5: Lowest idle time of the robot with more tasks
'''


class Auctioneer(RopodPyre):
    #  Bidding rules
    COMPLETION_TIME = 1
    COMPLETION_TIME_DISTANCE = 2
    MAKESPAN = 3
    MAKESPAN_DISTANCE = 4
    IDLE_TIME = 5

    def __init__(self, config_params):
        self.bidding_rule = config_params.bidding_rule
        self.zyre_params = config_params.task_allocator_zyre_params
        node_name = 'auctioneer_' + str(self.bidding_rule)
        super().__init__(node_name, self.zyre_params.groups, self.zyre_params.message_types, acknowledge=False)

        self.logger = logging.getLogger('auctioneer')
        self.logger.debug("This is a debug message")

        # Allocation time
        self.start_total_time = 0
        self.total_time = 0

        # List of tasks to allocate (type Task)
        self.tasks_to_allocate = list()
        # Triggers allocation of next task
        self.allocate_next_task = False

        # Bids received in one allocation iteration
        self.received_bids = list()
        self.received_no_bids = dict()
        self.n_round = 0

    def read_dataset(self, dataset_id):
        with open('datasets/' + dataset_id + ".yaml", 'r') as file:
            dataset = yaml.safe_load(file)
        print("dataset: ", dataset)
        return dataset

    def order_tasks(self, dataset):
        """Orders tasks in the dataset by their task_id"""
        ordered_tasks = collections.OrderedDict(sorted(dataset['tasks'].items()))
        return ordered_tasks

    def update_unallocated_tasks(self, tasks):
        """ Adds tasks to the list of unallocated tasks"""
        for task_id, task in tasks.items():
            self.tasks_to_allocate.append(Task.from_dict(task))

    def reinitialize_auction_variables(self):
        self.received_bids = list()
        self.received_no_bids = dict()
        self.n_round += 1

    def announce_task(self):
        if self.tasks_to_allocate and self.allocate_next_task:
            self.allocate_next_task = False
            self.reinitialize_auction_variables()

            self.logger.debug("Starting round: %s", self.n_round)
            self.logger.debug("Number of tasks to allocate: %s", len(self.tasks_to_allocate))

            # Create task announcement message that contains all unallocated tasks
            task_announcement = dict()
            task_announcement['header'] = dict()
            task_announcement['payload'] = dict()
            task_announcement['header']['type'] = 'TASK-ANNOUNCEMENT'
            task_announcement['header']['metamodel'] = 'ropod-msg-schema.json'
            task_announcement['header']['msgId'] = str(uuid.uuid4())
            task_announcement['header']['timestamp'] = int(round(time.time()) * 1000)
            task_announcement['payload']['metamodel'] = 'ropod-task-announcement-schema.json'
            task_announcement['payload']['round'] = self.n_round
            task_announcement['payload']['tasks'] = dict()

            for task in self.tasks_to_allocate:
                task_announcement['payload']['tasks'][task.id] = task.to_dict()

            self.logger.debug("Auctioneer announces tasks %s", [task.id for task in self.tasks_to_allocate])

            self.shout(task_announcement, 'TASK-ALLOCATION')

        elif not self.tasks_to_allocate and self.allocate_next_task:
            end_total_time = time.time()
            self.total_time = end_total_time - self.start_total_time

            # print("Reset variables and send DONE msg")
            self.reset_experiment_variables()

    def receive_msg_cb(self, msg_content):
        dict_msg = self.convert_zyre_msg_to_dict(msg_content)
        if dict_msg is None:
            return
        message_type = dict_msg['header']['type']

        if message_type == 'START':
            dataset_id = dict_msg['payload']['dataset_id']
            self.logger.debug("Received dataset %s", dataset_id)
            dataset = self.read_dataset(dataset_id)
            ordered_tasks = self.order_tasks(dataset)
            self.update_unallocated_tasks(ordered_tasks)
            self.allocate_next_task = True
            self.start_total_time = time.time()


if __name__ == '__main__':
    code_dir = os.path.abspath(os.path.dirname(__file__))
    main_dir = os.path.dirname(code_dir)

    config_params = ConfigFileReader.load("../config/config.yaml")

    with open('../config/logging.yaml', 'r') as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)


    # time.sleep(5)

    auctioneer = Auctioneer(config_params)
    auctioneer.start()

    try:
        while not auctioneer.terminated:
            auctioneer.announce_task()
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        # logging.info("Terminating %s proxy ...", ropod_id)
        auctioneer.shutdown()
        # logging.info("Exiting...")
        print("Exiting")
