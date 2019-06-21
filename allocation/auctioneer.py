from scheduler.structs.area import Area
from scheduler.structs.task import Task
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
        self.robots = config_params.ropods
        node_name = 'auctioneer'
        super().__init__(node_name, self.zyre_params.groups, self.zyre_params.message_types, acknowledge=False)

        self.logger = logging.getLogger('auctioneer')

        # {task_id: list of robots assigned to task_id}
        self.allocations = dict()

        # {robot_id: list of tasks scheduled to robot_id}
        self.schedule = dict()
        # Initialize schedule
        for robot_id in self.robots:
            self.schedule[robot_id] = list()

        # Allocation time
        self.start_total_time = 0
        self.total_time = 0

        # List of tasks to allocate (type Task)
        self.tasks_to_allocate = list()
        # Triggers allocation of next task
        self.allocate_next_task = False
        self.received_updated_schedule = True

        # Bids received in one allocation iteration
        self.received_bids = list()
        self.received_empty_bids = list()
        self.n_round = 0

    def read_dataset(self, dataset_id):
        with open('datasets/' + dataset_id + ".yaml", 'r') as file:
            dataset = yaml.safe_load(file)
        logging.info("Dataset: %s ", dataset)
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
        if self.tasks_to_allocate and self.allocate_next_task and self.received_updated_schedule:

            self.allocate_next_task = False
            self.received_updated_schedule = False
            self.reinitialize_auction_variables()

            self.logger.info("Starting round: %s", self.n_round)
            self.logger.info("Number of tasks to allocate: %s", len(self.tasks_to_allocate))

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
            self.terminate_allocation()

    def terminate_allocation(self):
        self.logger.info("Task allocation finished")
        end_total_time = time.time()
        self.total_time = end_total_time - self.start_total_time
        self.allocate_next_task = False
        self.n_round = 0
        self.send_done_msg()

    def check_n_received_bids(self):
        if (len(self.received_bids) + len(self.received_empty_bids)) == len(self.robots):
            self.logger.debug("The auctioneer has received a message from all robots")
            self.elect_winner()

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

        elif message_type == 'BID':
            bid = dict()
            bid['task_id'] = dict_msg['payload']['task_id']
            bid['robot_id'] = dict_msg['payload']['robot_id']
            bid['bid'] = dict_msg['payload']['bid']
            self.received_bids.append(bid)
            self.logger.debug("Received bid %s from %s", bid['bid'], bid['robot_id'])
            self.check_n_received_bids()

        elif message_type == 'EMPTY-BID':
            empty_bid = dict()
            empty_bid['task_ids'] = dict_msg['payload']['task_ids']
            empty_bid['robot_id'] = dict_msg['payload']['robot_id']
            self.received_empty_bids.append(empty_bid)
            self.logger.debug("Received empty bid from %s", empty_bid['robot_id'])
            self.check_n_received_bids()

        elif message_type == 'SCHEDULE':
            robot_id = dict_msg['payload']['robot_id']
            schedule = dict_msg['payload']['schedule']
            self.schedule[robot_id] = schedule
            self.received_updated_schedule = True
            self.logger.debug("Received schedule %s of robot %s", schedule, robot_id)

        elif message_type == "TERMINATE":
            self.logger.debug("Terminating auctioneer...")
            self.terminated = True
            # self.shutdown()

    def elect_winner(self):
        if self.received_bids:
            self.logger.debug("Number of bids received: %s", len(self.received_bids))
            lowest_bid = float('Inf')
            ordered_bids = dict()
            robots_tied = list()

            for bid in self.received_bids:
                if bid['task_id'] not in ordered_bids:
                    ordered_bids[bid['task_id']] = dict()
                    ordered_bids[bid['task_id']]['robot_id'] = list()
                    ordered_bids[bid['task_id']]['bids'] = list()

                ordered_bids[bid['task_id']]['bids'].append(bid['bid'])
                ordered_bids[bid['task_id']]['robot_id'].append(bid['robot_id'])

            # Order dictionary by task_id
            ordered_bids = collections.OrderedDict(sorted(ordered_bids.items()))

            # Resolve ties. If more than one task has the same bid,
            # select the task with the lowest_id.
            # If for that task, more than a robot has a bid, select the robot with the lowest id

            for task_id, values in ordered_bids.items():
                if min(values['bids']) < lowest_bid:
                    lowest_bid = min(values['bids'])
                    allocated_task = task_id
                    robots_tied = list()
                    for i, robot in enumerate(values['robot_id']):
                        if values['bids'][i] == lowest_bid:
                            robots_tied.append(values['robot_id'][i])

            if len(robots_tied) > 1:
                self.logger.debug("For task %s there is a tie between: %s", allocated_task, [robot_id for robot_id in robots_tied])
                robots_tied.sort(key=lambda x: int(x.split('_')[-1]))

            winning_robot = robots_tied[0]

            self.logger.info("Robot %s wins task %s", winning_robot, allocated_task)

            self.allocations[allocated_task] = [winning_robot]

            # Remove allocated task from self.tasks_to_allocate
            for i, task in enumerate(self.tasks_to_allocate):
                if task.id == allocated_task:
                    del self.tasks_to_allocate[i]

            self.announce_winner(allocated_task, winning_robot)

        else:
            logging.info("Tasks in unallocated tasks could not be allocated")
            for unallocated_task in self.unallocated_tasks:
                self.unsuccessful_allocations.append(unallocated_task.id)
            self.allocate_next_task = True
            self.unallocated_tasks = list()

    def announce_winner(self, allocated_task, winning_robot):
        allocation = dict()
        allocation['header'] = dict()
        allocation['payload'] = dict()
        allocation['header']['type'] = 'ALLOCATION'
        allocation['header']['metamodel'] = 'ropod-msg-schema.json'
        allocation['header']['msgId'] = str(uuid.uuid4())
        allocation['header']['timestamp'] = int(round(time.time()) * 1000)

        allocation['payload']['metamodel'] = 'ropod-allocation-schema.json'
        allocation['payload']['task_id'] = allocated_task
        allocation['payload']['winner_id'] = winning_robot

        self.logger.debug("Accouncing winner...")
        self.shout(allocation, 'TASK-ALLOCATION')

        # Sleep so that the winner robot has time to process the allocation
        # time.sleep(SLEEP_TIME)
        self.allocate_next_task = True

    def send_done_msg(self):
        done_msg = dict()
        done_msg['header'] = dict()
        done_msg['payload'] = dict()
        done_msg['header']['type'] = 'DONE'
        done_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        done_msg['header']['msgId'] = str(uuid.uuid4())
        done_msg['header']['timestamp'] = int(round(time.time()) * 1000)
        done_msg['payload']['metamodel'] = 'ropod-msg-schema.json'
        self.shout(done_msg, 'TASK-ALLOCATION')
        self.logger.debug("Done allocating tasks")


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
        logging.info("Auctioneer terminated; exiting")

    logging.info("Exiting auctioneer")
    auctioneer.shutdown()
