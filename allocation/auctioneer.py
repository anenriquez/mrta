from temporal.structs.area import Area
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

        super().__init__(node_name, self.zyre_params.groups, self.zyre_params.message_types)

        # with open('../config/logging.yaml', 'r') as f:
        #     config = yaml.safe_load(f.read())
        #     logging.config.dictConfig(config)

        self.logger = logging.getLogger('auctioneer')
        self.logger.debug("This is a debug message")

    #     self.received_bids = list()  # per round
    #     self.makespan = dict()
    #     self.completion_time = dict()
    #     self.idle_time = dict()
    #     self.travel_cost = dict()
    #     for robot_id in self.robots_info:
    #         self.travel_cost[robot_id] = 0.
    #
    # '''
    #     Every time announce_task is called, the allocation process is trigerred.
    #
    #     In TeSSIduo, an allocation process consists of one auction,
    #     which is composed of several rounds.
    #
    #     In an auction, TesSSIduo attempts to assign all tasks in the
    #     list of unallocated_tasks. One or more tasks can be
    #     assigned to each robot, i.e., each robot builds a schedule
    #     of tasks to be performed in the future.
    #
    #     An auction process consists of n rounds, where n is the
    #     number of tasks in the list of unallocated_tasks.
    #     n_rounds = len(self.unallocated_tasks)
    #
    #     One task is allocated per round until there are no more
    #     tasks left to allocate. Robots that already have allocated
    #     task(s) can participate in each round.
    #
    #     In each round:
    #         The auctionner announces all unallocated_tasks
    #         Each robot submits ist smallest bid
    #         The auctionner allocates the task with the smallest bid
    #         The auctioneer removes the allocated task from the
    #         list of unallocated_tasks
    #         A robot that received a task in the previous round can
    #         still participate in the next round (unlike Murdoch,
    #         the robot does not become 'unavailable')
    # '''
    # def announce_task(self):
    #
    #     if self.unallocated_tasks and self.allocate_next_task:
    #
    #         self.allocate_next_task = False
    #         self.reinitialize_auction_variables()
    #
    #         print("[INFO] Starting round: ", self.n_round)
    #         print("[INFO] Number of tasks to allocate: ", len(self.unallocated_tasks))
    #
    #         # Create task announcement message that contains all unallocated tasks
    #         task_announcement = dict()
    #         task_announcement['header'] = dict()
    #         task_announcement['payload'] = dict()
    #         task_announcement['header']['type'] = 'TASK-ANNOUNCEMENT'
    #         task_announcement['header']['metamodel'] = 'ropod-msg-schema.json'
    #         task_announcement['header']['msgId'] = str(uuid.uuid4())
    #         task_announcement['header']['timestamp'] = int(round(time.time()) * 1000)
    #
    #         task_announcement['payload']['metamodel'] = 'ropod-task-announcement-schema.json'
    #         task_announcement['payload']['round'] = self.n_round
    #         task_announcement['payload']['start_time'] = self.start_time
    #         task_announcement['payload']['tasks'] = dict()
    #
    #         for task in self.unallocated_tasks:
    #             task_announcement['payload']['tasks'][task.id] = task.to_dict()
    #
    #         self.verboseprint("[INFO] Auctioneer announces tasks.")
    #         self.shout(task_announcement, 'TASK-ALLOCATION')
    #         self.n_messages_sent += 1
    #         self.start_time_task = time.time()
    #
    #     elif not self.unallocated_tasks and self.allocate_next_task:
    #         # Sleep so that the auctioneer has time to process the last allocated task
    #         time.sleep(SLEEP_TIME)
    #
    #         end_total_time = time.time()
    #         self.total_time = end_total_time - self.start_total_time
    #
    #         print("Reset variables and send DONE msg")
    #         self.reset_experiment_variables()
    #
    # def reinitialize_auction_variables(self):
    #
    #     self.received_bids = list()
    #     self.received_no_bids = dict()
    #     self.n_bids_received = 0
    #     self.n_no_bids_received = 0
    #     self.n_round += 1
    #
    # def check_n_received_bids(self):
    #
    #     if (self.n_bids_received + self.n_no_bids_received) == len(self.robots_info):
    #         self.verboseprint("[INFO] Auctioneer has received a message from all robots")
    #         self.elect_winner()
    #
    # def receive_msg_cb(self, msg_content):
    #
    #     dict_msg = self.convert_zyre_msg_to_dict(msg_content)
    #     if dict_msg is None:
    #         return
    #
    #     message_type = dict_msg['header']['type']
    #
    #     if message_type == 'START':
    #         self.n_messages_received += 1
    #         self.start_time = dict_msg['payload']['start_time']
    #         self.dataset_id = dict_msg['payload']['dataset_id']
    #         self.batch_id = dict_msg['payload']['batch_id']
    #         self.verboseprint("Received start time {} dataset_id {} ".format(datetime.datetime.fromtimestamp(self.start_time), self.dataset_id))
    #
    #         if self.batch_id == 1:
    #             self.reset()
    #         self.start_total_time = time.time()
    #         self.get_assignment()
    #
    #     elif message_type == 'BID':
    #         self.n_messages_received += 1
    #         bid = dict()
    #         bid['task_id'] = dict_msg['payload']['task_id']
    #         bid['robot_id'] = dict_msg['payload']['robot_id']
    #         bid['bid'] = dict_msg['payload']['bid']
    #         self.received_bids.append(bid)
    #
    #         self.total_bids_received.append(bid)
    #         self.n_bids_received += 1
    #         self.verboseprint("[INFO] Received bid {}".format(bid))
    #         self.check_n_received_bids()
    #
    #     elif message_type == 'EMPTY-BID':
    #         self.n_messages_received += 1
    #         robot_id = dict_msg['payload']['robot_id']
    #         task_ids = dict_msg['payload']['task_ids']
    #
    #         no_bid = dict()
    #         no_bid['robot_id'] = robot_id
    #         # for task_id in task_ids:
    #         #     no_bid = dict()
    #         #     no_bid['robot_id'] = robot_id
    #         #     no_bid['task_id'] = task_id
    #
    #         self.total_no_bids_received.append(no_bid)
    #
    #         # if task_id in self.received_no_bids:
    #         #     self.received_no_bids[task_id] += 1
    #         # else:
    #         #     self.received_no_bids[task_id] = 1
    #
    #         self.n_no_bids_received += 1
    #         self.verboseprint("[INFO] Received NO-BID from", robot_id)
    #         self.check_n_received_bids()
    #
    #     elif message_type == 'SCHEDULE':
    #         self.n_messages_received += 1
    #         robot_id = dict_msg['payload']['robot_id']
    #         allocated_tasks_robot = dict_msg['payload']['allocated_tasks']
    #         schedule = dict_msg['payload']['schedule']
    #
    #         # makespan = dict_msg['payload']['makespan']
    #         # completion_time = dict_msg['payload']['completion_time']
    #         # idle_time = dict_msg['payload']['idle_time']
    #         # travel_cost = dict_msg['payload']['distance_robot']
    #
    #         self.order_allocation_robot[robot_id] = allocated_tasks_robot
    #         self.schedule[robot_id] = schedule
    #
    #         # self.makespan[robot_id] = makespan
    #         # self.completion_time[robot_id] = completion_time
    #         # self.idle_time[robot_id] = idle_time
    #         # self.travel_cost[robot_id] = travel_cost
    #
    #         self.verboseprint("[INFO] Auctioneer received schedule {} of robot {}".format(schedule, robot_id))
    #
    #     elif message_type == 'ROBOT-POSITION':
    #         robot_id = dict_msg['payload']['robot_id']
    #         position = dict_msg['payload']['position']
    #         new_position = Area()
    #         new_position.name = position
    #         self.robots_info[robot_id] = new_position
    #         print("[INFO] Robot {} changed initial position to {}".format(robot_id, position))
    #         self.n_messages_received = 0
    #
    #     elif message_type == "TERMINATE":
    #         self.terminate()
    #         print("Auctioneer received TERMINATE msg")
    #
    # def elect_winner(self):
    #
    #     if self.received_bids:
    #         self.verboseprint("[INFO] Number of bids received: ", len(self.received_bids))
    #         lowest_bid = float('Inf')
    #         ordered_bids = dict()
    #         robots_tied = list()
    #
    #         for bid in self.received_bids:
    #             if bid['task_id'] not in ordered_bids:
    #                 ordered_bids[bid['task_id']] = dict()
    #                 ordered_bids[bid['task_id']]['robot_id'] = list()
    #                 ordered_bids[bid['task_id']]['bids'] = list()
    #
    #             ordered_bids[bid['task_id']]['bids'].append(bid['bid'])
    #             ordered_bids[bid['task_id']]['robot_id'].append(bid['robot_id'])
    #
    #         # Order dictionary by task_id
    #         ordered_bids = collections.OrderedDict(sorted(ordered_bids.items()))
    #
    #         # Resolve ties. If more than one task has the same bid,
    #         # select the task with the lowest_id.
    #         # If for that task, more than a robot has a bid, select the robot with the lowest id
    #
    #         for task_id, values in ordered_bids.items():
    #             if min(values['bids']) < lowest_bid:
    #
    #                 lowest_bid = min(values['bids'])
    #                 allocated_task = task_id
    #                 robots_tied = list()
    #                 for i, robot in enumerate(values['robot_id']):
    #                     if values['bids'][i] == lowest_bid:
    #                         robots_tied.append(values['robot_id'][i])
    #
    #         if len(robots_tied) > 1:
    #             self.verboseprint("[INFO] For task {} there is a tie between: {}".format(allocated_task, [robot_id for robot_id in robots_tied]))
    #             robots_tied.sort(key=lambda x: int(x.split('_')[-1]))
    #
    #         winning_robot = robots_tied[0]
    #
    #         print("Winning robot: ", winning_robot)
    #
    #         self.verboseprint("[INFO] Robot {} wins task {}".format(winning_robot, allocated_task))
    #
    #         self.allocations[allocated_task] = [winning_robot]
    #
    #         # Remove allocated task from self.unallocated_tasks
    #         for i, task in enumerate(self.unallocated_tasks):
    #             if task.id == allocated_task:
    #                 self.verboseprint("[INFO] Removing task {} from unallocated_tasks".format(task.id))
    #                 del self.unallocated_tasks[i]
    #                 self.verboseprint("[INFO] Adding task {} to allocated_tasks".format(task.id))
    #                 self.allocated_tasks[task.id] = task
    #
    #         end_time_task = time.time()
    #         time_to_allocate = round(end_time_task - self.start_time_task, 3)
    #         self.time_to_allocate[allocated_task] = time_to_allocate
    #         self.order_allocation[self.n_round] = [allocated_task, time_to_allocate]
    #         self.announce_winner(allocated_task, winning_robot)
    #
    #     else:
    #         print("[INFO] Tasks in unallocated tasks could not be allocated")
    #         for unallocated_task in self.unallocated_tasks:
    #             self.unsuccessful_allocations.append(unallocated_task.id)
    #         self.allocate_next_task = True
    #         self.unallocated_tasks = list()
    #
    # def announce_winner(self, allocated_task, winning_robot):
    #
    #     # Create allocation message
    #     allocation = dict()
    #     allocation['header'] = dict()
    #     allocation['payload'] = dict()
    #     allocation['header']['type'] = 'ALLOCATION'
    #     allocation['header']['metamodel'] = 'ropod-msg-schema.json'
    #     allocation['header']['msgId'] = str(uuid.uuid4())
    #     allocation['header']['timestamp'] = int(round(time.time()) * 1000)
    #
    #     allocation['payload']['metamodel'] = 'ropod-allocation-schema.json'
    #     allocation['payload']['task_id'] = allocated_task
    #     allocation['payload']['winner_id'] = winning_robot
    #
    #     self.verboseprint("[INFO] Accouncing winner...")
    #     self.shout(allocation, 'TASK-ALLOCATION')
    #     self.n_messages_sent += 1
    #
    #     # Sleep so that the winner robot has time to process the allocation
    #     time.sleep(SLEEP_TIME)
    #     self.allocate_next_task = True


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
        while True:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        # logging.info("Terminating %s proxy ...", ropod_id)
        robot.shutdown()
        # logging.info("Exiting...")
        print("Exiting")
