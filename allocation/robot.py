import copy
import uuid
import time
import numpy as np
import os
import argparse
import logging
import logging.config
import yaml
from ropod.pyre_communicator.base_class import RopodPyre
# from allocation.config.config_file_reader import ConfigFileReader
from scheduler.structs.task import Task
from scheduler.scheduler import Scheduler
from allocation.api.zyre import ZyreAPI
from allocation.config.loader import Config
from utils.config_logger import config_logger


'''  Implements the TeSSI algorithm with different bidding rules:

    - Rule 1: Lowest completion time (last task finish time - first task start time)
    - Rule 2: Lowest combination of completion time and travel distance_robot
    - Rule 3: Lowest makespan (finish time of the last task in the schedule)
    - Rule 4: Lowest combination of makespan and travel distance_robot
    - Rule 5: Lowest idle time of the robot with more tasks
'''
MAX_SEED = 2 ** 31 - 1


class Robot(object):
    #  Bidding rules
    COMPLETION_TIME = 1
    COMPLETION_TIME_DISTANCE = 2
    MAKESPAN = 3
    MAKESPAN_DISTANCE = 4
    IDLE_TIME = 5

    def __init__(self, robot_id, bidding_rule, scheduling_method, api_config, auctioneer):
        self.id = robot_id
        self.bidding_rule = bidding_rule
        self.scheduler = Scheduler(scheduling_method)
        self.auctioneer = auctioneer

        zyre_config = api_config.get('zyre')  # Arguments for the zyre_base class
        zyre_config['node_name'] = robot_id + '_proxy'

        print("Zyre config: ", zyre_config)

        # super().__init__(zyre_config)

        self.api = ZyreAPI(zyre_config)

        self.api.add_callback(self, 'START', 'start_cb')
        self.api.add_callback(self, 'TASK-ANNOUNCEMENT', 'task_announcement_cb')
        self.api.add_callback(self, 'ALLOCATION', 'allocation_cb')
        self.api.add_callback(self, 'TERMINATE', 'terminate_cb')


        # zyre_params = config_params.task_allocator_zyre_params
        # self.api(robot_id, zyre_params.groups, zyre_params.message_types, acknowledge=False)

        # self.zyre_params = config_params.task_allocator_zyre_params
        #
        # super().__init__(self.id, self.zyre_params.groups, self.zyre_params.message_types, acknowledge=False)

        config_logger('../config/logging.yaml')
        self.logger = logging.getLogger('robot.%s' % robot_id)



        self.dispatch_graph_round = self.scheduler.get_temporal_network()

        self.scheduled_tasks = self.scheduler.get_scheduled_tasks()

        self.dataset_start_time = 0
        self.idle_time = 0.
        self.distance = 0.

        self.bid_round = 0.
        self.dispatch_graph_round = self.scheduler.get_temporal_network()

        # Weighting factor used for the dual bidding rule
        self.alpha = 0.1

    def reinitialize_auction_variables(self):
        self.bid_round = None
        self.dispatch_graph_round = self.scheduler.get_temporal_network()

    def start_cb(self, msg):
        self.dataset_start_time = msg['payload']['start_time']
        self.logger.debug("Received dataset start time %s", self.dataset_start_time)

    def task_announcement_cb(self, msg):
        self.reinitialize_auction_variables()
        n_round = msg['payload']['round']
        tasks = msg['payload']['tasks']
        self.compute_bids(tasks, n_round)

    def allocation_cb(self, msg):
        task_id = msg['payload']['task_id']
        winner_id = msg['payload']['winner_id']
        if winner_id == self.id:
            self.allocate_to_robot(task_id)

    def terminate_cb(self, msg):
        self.logger.debug("Terminating robot...")
        self.api.terminated = True

    # def receive_msg_cb(self, msg_content):
    #     # self.receive_msg_cb(msg_content)
    #
    #     dict_msg = self.convert_zyre_msg_to_dict(msg_content)
    #     if dict_msg is None:
    #         return
    #     message_type = dict_msg['header']['type']
    #
    #     if message_type == 'START':
    #         self.dataset_start_time = dict_msg['payload']['start_time']
    #         self.logger.debug("Received dataset start time %s", self.dataset_start_time)
    #
    #     elif message_type == 'TASK-ANNOUNCEMENT':
    #         self.reinitialize_auction_variables()
    #         n_round = dict_msg['payload']['round']
    #         tasks = dict_msg['payload']['tasks']
    #         self.compute_bids(tasks, n_round)
    #
    #     elif message_type == "ALLOCATION":
    #         task_id = dict_msg['payload']['task_id']
    #         winner_id = dict_msg['payload']['winner_id']
    #         if winner_id == self.id:
    #             self.allocate_to_robot(task_id)
    #
    #     elif message_type == "TERMINATE":
    #         self.logger.debug("Terminating robot...")
    #         self.api.terminated = True
    #         # self.shutdown()

    def compute_bids(self, tasks, n_round):
        bids = dict()
        no_bids = list()

        for task_id, task_info in tasks.items():
            task = Task.from_dict(task_info)
            self.logger.debug("Computing bid of task %s", task.id)
            # Insert task in each possible position of the stnu
            best_bid, best_dispatch_graph = self.insert_task(task)

            if best_bid != np.inf:
                bids[task_id] = dict()
                bids[task_id]['bid'] = best_bid
                bids[task_id]['dispatch_graph'] = best_dispatch_graph

            else:
                no_bids.append(task_id)

        if bids:
            # Send the smallest bid
            task_id_bid, smallest_bid = self.get_smallest_bid(bids, n_round)
            self.send_bid(n_round, task_id_bid, smallest_bid)
        else:
            # Send an empty bid with task ids of tasks that could not be allocated
            self.send_no_bid(n_round, no_bids)

    def insert_task(self, task):
        best_bid = float('Inf')
        best_schedule = list()

        n_scheduled_tasks = len(self.scheduled_tasks)

        for i in range(0, n_scheduled_tasks + 1):
            # TODO check if the robot can make it to the first task in the schedule, if not, return

            self.scheduler.add_task(task, i+1)

            self.logger.debug("STN: %s", self.scheduler.get_temporal_network())

            result = self.scheduler.get_dispatch_graph()
            if result is not None:
                metric, dispatch_graph = result

                bid = self.compute_bid(dispatch_graph, metric)
                if bid < best_bid:
                    best_bid = bid
                    best_dispatch_graph = copy.deepcopy(dispatch_graph)

            # Restore schedule for the next iteration
            self.scheduler.remove_task(i+1)

        return best_bid, best_dispatch_graph

    def rule_completion_time(self, dispatch_graph, metric):
        completion_time = dispatch_graph.get_completion_time()
        self.logger.debug("Completion time: %s", completion_time)

        if self.scheduler.get_scheduling_method() == 'fpc':
            bid = completion_time

        elif self.scheduler.get_scheduling_method() == 'srea':
            # metric is the level of risk. A smaller value is preferable
            self.logger.debug("Alpha: %s ", metric)
            bid = completion_time/metric

        elif self.scheduler.get_scheduling_method() == 'dsc_lp':
            # metric is the degree of strong controllability. A larger value is preferable
            self.logger.debug("DSC: %s ", metric)
            bid = completion_time * metric

        return bid

    def compute_bid(self, dispatch_graph, metric):

        if self.bidding_rule == self.COMPLETION_TIME:
            bid = self.rule_completion_time(dispatch_graph, metric)
            self.logger.debug("Bid: %s", bid)

        # TODO: Maybe add other bidding rules
        return bid

    def compute_distance(self, schedule):
        ''' Computes the travel cost (distance traveled) for performing all
        tasks in the schedule (list of tasks)
        '''
        # TODO: Maybe we don't need this
        distance = 0
        return distance

    def get_smallest_bid(self, bids, n_round):
        '''
        Get the smallest bid among all bids.
        Each robot submits only its smallest bid in each round
        If two or more tasks have the same bid, the robot bids for the task with the lowest task_id
        '''
        smallest_bid = dict()
        smallest_bid['bid'] = np.inf
        task_id_bid = None
        lowest_task_id = ''

        for task_id, bid_info in bids.items():
            if bid_info['bid'] < smallest_bid['bid']:
                smallest_bid = copy.deepcopy(bid_info)
                task_id_bid = task_id
                lowest_task_id = task_id_bid

            elif bid_info['bid'] == smallest_bid['bid'] and task_id < lowest_task_id:
                smallest_bid = copy.deepcopy(bid_info)
                task_id_bid = task_id
                lowest_task_id = task_id_bid

        if smallest_bid != np.inf:
            return task_id_bid, smallest_bid

    def send_bid(self, n_round, task_id, bid):
        ''' Create bid_msg and send it to the auctioneer '''
        bid_msg = dict()
        bid_msg['header'] = dict()
        bid_msg['payload'] = dict()
        bid_msg['header']['type'] = 'BID'
        bid_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        bid_msg['header']['msgId'] = str(uuid.uuid4())
        bid_msg['header']['timestamp'] = int(round(time.time()) * 1000)

        bid_msg['payload']['metamodel'] = 'ropod-bid-schema.json'
        bid_msg['payload']['robot_id'] = self.id
        bid_msg['payload']['n_round'] = n_round
        bid_msg['payload']['task_id'] = task_id
        bid_msg['payload']['bid'] = bid['bid']

        self.bid_round = bid['bid']
        # self.scheduled_tasks_round = bid['scheduled_tasks']
        self.dispatch_graph_round = bid['dispatch_graph']

        self.scheduled_tasks = self.dispatch_graph_round.get_scheduled_tasks()
        tasks = [task for task in self.scheduled_tasks]

        self.logger.info("Round %s: Robod_id %s bids %s for task %s and scheduled_tasks %s", n_round, self.id, self.bid_round, task_id, tasks)
        self.api.whisper(bid_msg, peer=self.auctioneer)
        # self.api.shout(bid_msg)
        # self.whisper(bid_msg, peer='zyre_api')

    def send_no_bid(self, n_round, no_bids):
        '''
        Create no_bid_msg for each task in no_bids and send it to the auctioneer
        '''
        no_bid_msg = dict()
        no_bid_msg['header'] = dict()
        no_bid_msg['payload'] = dict()
        no_bid_msg['header']['type'] = 'NO-BID'
        no_bid_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        no_bid_msg['header']['msgId'] = str(uuid.uuid4())
        no_bid_msg['header']['timestamp'] = int(round(time.time()) * 1000)

        no_bid_msg['payload']['metamodel'] = 'ropod-bid-schema.json'
        no_bid_msg['payload']['robot_id'] = self.id
        no_bid_msg['payload']['n_round'] = n_round
        no_bid_msg['payload']['task_ids'] = list()

        for task_id in no_bids:
            no_bid_msg['payload']['task_ids'].append(task_id)

        self.logger.info("Round %s: Robot id %s sends empty bid for tasks %s", n_round, self.id, no_bids)
        self.api.whisper(no_bid_msg, peer=self.auctioneer)

    def allocate_to_robot(self, task_id):
        # Update the dispatch_graph
        self.scheduler.temporal_network = copy.deepcopy(self.dispatch_graph_round)

        self.logger.info("Robot %s allocated task %s", self.id, task_id)

        tasks = [task for task in self.scheduled_tasks]

        self.logger.info("Tasks scheduled to robot %s:%s", self.id, tasks)

        self.send_schedule()

    def send_schedule(self):
        # TODO: Send dispatch_graph instead of scheduled_tasks
        ''' Sends the updated schedule of the robot to the auctioneer.
        '''
        schedule_msg = dict()
        schedule_msg['header'] = dict()
        schedule_msg['payload'] = dict()
        schedule_msg['header']['type'] = 'SCHEDULE'
        schedule_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        schedule_msg['header']['msgId'] = str(uuid.uuid4())
        schedule_msg['header']['timestamp'] = int(round(time.time()) * 1000)
        schedule_msg['payload']['metamodel'] = 'ropod-msg-schema.json'
        schedule_msg['payload']['robot_id'] = self.id
        schedule_msg['payload']['schedule'] = list()
        for i, task_id in enumerate(self.scheduled_tasks):
            schedule_msg['payload']['schedule'].append(task_id)

        self.api.whisper(schedule_msg, peer=self.auctioneer)

        self.logger.debug("Robot sent its updated schedule to the auctioneer.")


if __name__ == '__main__':
    # code_dir = os.path.abspath(os.path.dirname(__file__))
    # main_dir = os.path.dirname(code_dir)

    # with open('../config/logging.yaml', 'r') as f:
    #     log_config = yaml.safe_load(f.read())
    #     logging.config.dictConfig(log_config)

    config = Config("../config/config-v2.yaml", False)

    # config_params = config.get_config_params()
    # print("Config params: ", config_params)

    parser = argparse.ArgumentParser()
    parser.add_argument('robot_id', type=str, help='example: ropod_001')
    args = parser.parse_args()
    robot_id = args.robot_id

    robot_config = config.configure_robot_proxy(robot_id)
    robot = Robot(**robot_config)


    # zyre_api = config.configure_api(robot_id)
    # api_config = config_params.get('api')
    # zyre_config = api_config.get('zyre')
    # zyre_api = ZyreAPI(zyre_config)


    # zyre_api = ZyreAPI(robot_id, zyre_params.groups, zyre_params.message_types, acknowledge=False)

    # robot = Robot(robot_id, config_params, zyre_api)

    # robot.api.start()
    # robot.api.start()

    try:
        while not robot.api.terminated:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Robot terminated; exiting")

    logging.info("Exiting robot")
    # robot.api.shutdown()
    robot.api.shutdown()
