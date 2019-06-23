from scheduler.structs.task import Task
import uuid
import time
import collections
import logging
import logging.config
import yaml
from datetime import timedelta
from allocation.config.loader import Config
from allocation.utils.config_logger import config_logger

SLEEP_TIME = 0.350

'''  Implements the TeSSI algorithm with different bidding rules:

    - Rule 1: Lowest completion time (last task finish time - first task start time)
    - Rule 2: Lowest combination of completion time and travel distance_robot
    - Rule 3: Lowest makespan (finish time of the last task in the schedule)
    - Rule 4: Lowest combination of makespan and travel distance_robot
    - Rule 5: Lowest idle time of the robot with more tasks
'''


class Auctioneer(object):
    #  Bidding rules
    COMPLETION_TIME = 1
    COMPLETION_TIME_DISTANCE = 2
    MAKESPAN = 3
    MAKESPAN_DISTANCE = 4
    IDLE_TIME = 5

    def __init__(self, bidding_rule, robot_ids, api, auction_time=5, **kwargs):

        self.logger = logging.getLogger('auctioneer')

        self.bidding_rule = bidding_rule
        self.robots = robot_ids
        self.api = api
        self.auction_time = timedelta(seconds=auction_time)

        self.api.add_callback(self, 'START', 'start_cb')
        self.api.add_callback(self, 'BID', 'bid_cb')
        self.api.add_callback(self, 'NO-BID', 'no_bid_cb')
        self.api.add_callback(self, 'SCHEDULE', 'schedule_cb')
        self.api.add_callback(self, 'TERMINATE', 'terminate_cb')

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
        self.received_no_bids = list()
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

            self.api.shout(task_announcement, 'TASK-ALLOCATION')

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
        print("Check n recevied Bids")
        print("bids", len(self.received_bids))
        print("robots", len(self.robots))
        if (len(self.received_bids) + len(self.received_no_bids)) == len(self.robots):
            self.logger.debug("The auctioneer has received a message from all robots")
            self.elect_winner()

    def start_cb(self, msg):
        dataset_id = msg['payload']['dataset_id']
        self.logger.debug("Received dataset %s", dataset_id)
        dataset = self.read_dataset(dataset_id)
        ordered_tasks = self.order_tasks(dataset)
        self.update_unallocated_tasks(ordered_tasks)
        self.allocate_next_task = True
        self.start_total_time = time.time()

    def bid_cb(self, msg):
        self.logger.debug("Receiving bid...")
        bid = dict()
        bid['task_id'] = msg['payload']['task_id']
        bid['robot_id'] = msg['payload']['robot_id']
        bid['bid'] = msg['payload']['bid']
        self.received_bids.append(bid)
        self.logger.debug("Received bid %s from %s", bid['bid'], bid['robot_id'])
        self.check_n_received_bids()

    def no_bid_cb(self, msg):
        no_bid = dict()
        no_bid['task_ids'] = msg['payload']['task_ids']
        no_bid['robot_id'] = msg['payload']['robot_id']
        self.received_no_bids.append(no_bid)
        self.logger.debug("Received no-bid from %s", no_bid['robot_id'])
        self.check_n_received_bids()

    def schedule_cb(self, msg):
        robot_id = msg['payload']['robot_id']
        schedule = msg['payload']['schedule']
        self.schedule[robot_id] = schedule
        self.received_updated_schedule = True
        self.logger.debug("Received schedule %s of robot %s", schedule, robot_id)

    def terminate_cb(self, msg):
        self.logger.debug("Terminating auctioneer...")
        self.api.terminated = True

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
        self.api.shout(allocation, 'TASK-ALLOCATION')

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
        self.api.shout(done_msg)
        self.logger.debug("Done allocating tasks")


if __name__ == '__main__':

    config_logger('../config/logging.yaml')
    config = Config("../config/config.yaml")

    auctioneer_config = config.configure_auctioneer()
    auctioneer = Auctioneer(**auctioneer_config)

    try:
        while not auctioneer.api.terminated:
            auctioneer.announce_task()
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Auctioneer terminated; exiting")

    logging.info("Exiting auctioneer")
    auctioneer.api.shutdown()
