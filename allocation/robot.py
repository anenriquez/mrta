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
from allocation.config.config_file_reader import ConfigFileReader
from temporal.structs.task import Task
from temporal.networks.stnu import STNU

'''  Implements the TeSSI algorithm with different bidding rules:

    - Rule 1: Lowest completion time (last task finish time - first task start time)
    - Rule 2: Lowest combination of completion time and travel distance_robot
    - Rule 3: Lowest makespan (finish time of the last task in the schedule)
    - Rule 4: Lowest combination of makespan and travel distance_robot
    - Rule 5: Lowest idle time of the robot with more tasks
'''


class Robot(RopodPyre):
    #  Bidding rules
    COMPLETION_TIME = 1
    COMPLETION_TIME_DISTANCE = 2
    MAKESPAN = 3
    MAKESPAN_DISTANCE = 4
    IDLE_TIME = 5

    def __init__(self, robot_id, config_params):
        self.id = robot_id
        self.bidding_rule = config_params.bidding_rule
        self.zyre_params = config_params.task_allocator_zyre_params

        super().__init__(self.id, self.zyre_params.groups, self.zyre_params.message_types)

        # with open('../config/logging.yaml', 'r') as f:
        #     config = yaml.safe_load(f.read())
        #     logging.config.dictConfig(config)

        self.logger = logging.getLogger('robot: %s' % robot_id)
        self.logger.debug("This is a debug message")

        self.scheduled_tasks = list()
    #     self.minimal_stn = list()
    #
    #     # Look up table to store travel time from source to destination
    #     # travel_times['source-destination'] = travel_time
    #     self.travel_times = dict()
    #
    #     self.received_tasks_round = list()
    #     self.bid_round = 0.
    #     self.scheduled_tasks_round = list()
    #     self.minimal_stn_round = list()
    #
    #     self.makespan = 0.
    #     self.completion_time = 0.
    #     self.idle_time = 0.
    #     self.distance = 0.
    #
    #     # Weighting factor used for the dual bidding rule
    #     self.alpha = 0.1
    #
    #     self.verbose_mrta = verbose_mrta
    #     self.verboseprint = print if self.verbose_mrta else lambda *a, **k: None
    #
    # def receive_msg_cb(self, msg_content):
    #     dict_msg = self.convert_zyre_msg_to_dict(msg_content)
    #     if dict_msg is None:
    #         return
    #     message_type = dict_msg['header']['type']
    #
    #     if message_type == 'START':
    #         self.start_time = dict_msg['payload']['start_time']
    #         print("[INFO] Robot {} received start time".format(self.id))
    #         # time.sleep(0.8)
    #
    #     elif message_type == "CLEAN-SCHEDULE":
    #         self.clean_schedule()
    #
    #     elif message_type == 'RESET':
    #         self.reset_variables()
    #
    #     elif message_type == 'TASK-ANNOUNCEMENT':
    #         self.reinitialize_auction_variables()
    #         n_round = dict_msg['payload']['round']
    #         tasks = dict_msg['payload']['tasks']
    #         self.start_time = dict_msg['payload']['start_time']
    #         self.expand_schedule(tasks, n_round)
    #
    #     elif message_type == "ALLOCATION":
    #         allocation = dict()
    #         allocation['task_id'] = dict_msg['payload']['task_id']
    #         allocation['winner_id'] = dict_msg['payload']['winner_id']
    #         if allocation['winner_id'] == self.id:
    #             self.allocate_to_robot(allocation['task_id'])
    #
    #     elif message_type == "TERMINATE":
    #         print("Robot received TERMINATE msg")
    #         self.terminate()
    #
    # def reinitialize_auction_variables(self):
    #     self.received_tasks_round = list()
    #     self.bid_round = None
    #     self.scheduled_tasks_round = list()
    #     self.minimal_stn_round = list()
    #
    # ''' Receives a list of tasks. Computes a bid for each task.
    # Returns a bid dictionary.
    # '''
    # def expand_schedule(self, tasks, n_round):
    #     bids = dict()
    #     empty_bids = list()
    #
    #     for task_id, task_info in tasks.items():
    #         task = Task.from_dict(task_info)
    #         self.received_tasks_round.append(task)
    #
    #         # Insert task in each possible position of the list of scheduled tasks
    #         best_bid, best_schedule, best_stn = self.insert_task(task)
    #
    #         if best_bid != np.inf:
    #             bids[task_id] = dict()
    #             bids[task_id]['bid'] = best_bid
    #             bids[task_id]['scheduled_tasks'] = best_schedule
    #             bids[task_id]['stn'] = best_stn
    #         else:
    #             empty_bids.append(task_id)
    #
    #     if bids:
    #         # Send the smallest bid
    #         task_id_bid, smallest_bid = self.get_smallest_bid(bids, n_round)
    #         self.send_bid(n_round, task_id_bid, smallest_bid)
    #     else:
    #         # Send an empty bid with task ids of tasks that could not be allocated
    #         self.send_empty_bid(n_round, empty_bids)
    #
    # ''' Computes the travel cost (distance_robot traveled) for performing all
    # tasks in the schedule (list of tasks)
    # '''
    # def compute_distance(self, schedule):
    #     distance = 0
    #
    #     # The initial robot position for perfoming the tasks in the schedule
    #     prev_position = self.position
    #
    #     for task in schedule:
    #         distance += self.get_travel_time(prev_position, task.pickup_pose) + self.get_travel_time(task.pickup_pose, task.delivery_pose)
    #
    #         prev_position = task.delivery_pose
    #
    #     return distance
    #
    # def compute_bid(self, stn):
    #     self.update_time_schedule(stn)
    #
    #     if self.bidding_rule == self.COMPLETION_TIME:
    #         bid = self.compute_completion_time()
    #
    #     elif self.bidding_rule == self.COMPLETION_TIME_DISTANCE:
    #         completion_time = self.compute_completion_time()
    #         distance = self.compute_distance(self.scheduled_tasks)
    #         bid = (self.alpha * completion_time) + (1 - self.alpha) * (distance - self.distance)
    #
    #     elif self.bidding_rule == self.MAKESPAN:
    #         bid = self.compute_makespan()
    #
    #     elif self.bidding_rule == self.MAKESPAN_DISTANCE:
    #         makespan = self.compute_makespan()
    #         distance = self.compute_distance(self.scheduled_tasks)
    #         bid = (self.alpha * makespan) + (1 - self.alpha) * (distance - self.distance)
    #
    #     elif self.bidding_rule == self.IDLE_TIME:
    #         idle_time = self.compute_idle_time()
    #         bid = idle_time - self.idle_time
    #
    #     return bid
    #
    # ''' Insert task in each possible position of the list of scheduled
    # tasks.
    # '''
    # def insert_task(self, task):
    #     best_bid = float('Inf')
    #     best_schedule = list()
    #     best_stn = list()
    #
    #     n_scheduled_tasks = len(self.scheduled_tasks)
    #
    #     for i in range(0, n_scheduled_tasks + 1):
    #         self.scheduled_tasks.insert(i, task)
    #         stn = self.build_stn(self.scheduled_tasks, task, i)
    #         if stn:
    #             minimal_stn = self.floyd_warshall(stn)
    #             if self.is_consistent(minimal_stn):
    #                 bid = self.compute_bid(minimal_stn)
    #                 if bid < best_bid:
    #                     best_bid = bid
    #                     best_schedule = copy.deepcopy(self.scheduled_tasks)
    #                     best_stn = copy.deepcopy(minimal_stn)
    #
    #         # Restore new_schedule for the next iteration
    #         self.scheduled_tasks.pop(i)
    #
    #     return best_bid, best_schedule, best_stn
    #
    # '''Calculates the time for going from the robot's position to the pickup location of the first task in the schedule.
    # The earliest_start_time at which the first task will be executed is whatever value is bigger (travel time to the task or earliest_start_time). The STN can only  be build if such value is smaller than the latest_start_time.
    # '''
    # def travel_constraint_first_task(self, task):
    #     travel_time = self.get_distance(self.position, task.pickup_pose) + self.start_time
    #     earliest_start_time = max(travel_time, task.earliest_start_time)
    #
    #     if earliest_start_time < task.latest_start_time:
    #         return earliest_start_time
    #     else:
    #         return False
    #
    # '''
    # Builds a STN for the tasks in new_schedule
    # Each edge is represented as a list
    # [start_vertex, end_vertex, weight]
    # All edges are stored in a list
    # '''
    # def build_stn(self, new_schedule, task, position):
    #     edges = list()
    #     stn = list()
    #     # Check if the robot can make it to the pickup location of task
    #     earliest_start_time = self.travel_constraint_first_task(new_schedule[0])
    #
    #     if earliest_start_time:
    #         for position, task in enumerate(new_schedule):
    #             start = position * 2 + 1
    #             end = start + 1
    #             l_s_t = [0, start, task.latest_start_time]
    #             l_f_t = [0, end, task.latest_finish_time]
    #             e_f_t = [end, 0, -task.earliest_finish_time]
    #             duration = [end, start, -task.estimated_duration]
    #             edges.append(l_s_t)
    #             edges.append(l_f_t)
    #             edges.append(e_f_t)
    #             edges.append(duration)
    #
    #             if position == 0:
    #                 e_s_t = [start, 0, -earliest_start_time]
    #             else:
    #                 e_s_t = [start, 0, -task.earliest_start_time]
    #                 travel_time = self.get_travel_time(new_schedule[position - 1].delivery_pose, task.pickup_pose)
    #                 # print("Travel time from {} to {}: {} ".format(new_schedule[position - 1].id, task.id, travel_time))
    #                 t_t = [start, start - 1, -travel_time]
    #                 edges.append(t_t)
    #
    #             edges.append(e_s_t)
    #
    #         # Initialize the stn with entries equal to inf
    #         n_tasks = len(new_schedule)
    #         n_vertices = n_tasks * 2 + 1
    #
    #         for i in range(0, n_vertices):
    #             stn.append([])
    #             for j in range(0, n_vertices):
    #                 stn[i].append(float('Inf'))
    #
    #         # Store edges with their weights
    #         for i in range(0, len(edges)):
    #             for info in edges:
    #                 start_point = info[0]
    #                 end_point = info[1]
    #                 weight = info[2]
    #                 stn[start_point][end_point] = weight
    #
    #         # Set paths of each vertex to itself to zero
    #         for i in range(0, n_vertices):
    #             stn[i][i] = 0
    #
    #     return stn
    #
    # ''' Returns the estimated time the robot will need to travel
    # from the delivery pose of the previous task to the pickup pose
    # of the next task
    # '''
    # def get_travel_time(self, source, destination):
    #     if source.name + '-' + destination.name in self.travel_times:
    #         travel_time = self.travel_times[source.name + '-' + destination.name]
    #     else:
    #         travel_time = self.get_distance(source, destination)
    #         self.travel_times[source.name + '-' + destination.name] = travel_time
    #
    #     return travel_time
    #
    # '''
    # Computes the smallest distances between each pair of vertices in the stn.
    # '''
    # def floyd_warshall(self, stn):
    #     n_vertices = len(stn)
    #     for k in range(0, n_vertices):
    #         for i in range(0, n_vertices):
    #             for j in range(0, n_vertices):
    #                 if stn[i][j] > stn[i][k] + stn[k][j]:
    #                     stn[i][j] = stn[i][k] + stn[k][j]
    #     return stn
    #
    # '''
    # The stn is consistent if it does not contain negative cycles
    # '''
    # def is_consistent(self, minimal_stn):
    #     consistent = True
    #     n_vertices = len(minimal_stn)
    #     # check for negative cycles
    #     for i in range(0, n_vertices):
    #         if minimal_stn[i][i] != 0:
    #             consistent = False
    #
    #     return consistent
    #
    # '''
    # Returns the completion time (time between the lowest interval of the first scheduled task and the lowest interval of the last scheduled task)
    # '''
    # def compute_completion_time(self):
    #     first_task = self.scheduled_tasks[0]
    #     last_task = self.scheduled_tasks[-1]
    #     completion_time = round(last_task.finish_time - first_task.start_time, 2)
    #     return completion_time
    #
    # def compute_makespan(self):
    #     last_task = self.scheduled_tasks[-1]
    #     makespan = last_task.finish_time
    #     return makespan
    #
    # def compute_idle_time(self):
    #     idle_time = 0
    #     for i, task in enumerate(self.scheduled_tasks):
    #         if i == 0:
    #             idle_time += self.get_travel_time(self.position, task.pickup_pose)
    #
    #         elif i < len(self.scheduled_tasks):
    #             previous_task = self.scheduled_tasks[i-1]
    #
    #             idle_time += round(task.start_time - previous_task.finish_time, 2)
    #
    #     return idle_time
    #
    # '''
    # Get the smallest bid among all bids.
    # Each robot submits only its smallest bid in each round
    # If two or more tasks have the same bid, the robot bids for the task with the lowest task_id
    # '''
    # def get_smallest_bid(self, bids, n_round):
    #     smallest_bid = dict()
    #     smallest_bid['bid'] = np.inf
    #     task_id_bid = None
    #     lowest_task_id = ''
    #
    #     for task_id, bid_info in bids.items():
    #         if bid_info['bid'] < smallest_bid['bid']:
    #             smallest_bid = copy.deepcopy(bid_info)
    #             task_id_bid = task_id
    #             lowest_task_id = task_id_bid
    #
    #         elif bid_info['bid'] == smallest_bid['bid'] and task_id < lowest_task_id:
    #             smallest_bid = copy.deepcopy(bid_info)
    #             task_id_bid = task_id
    #             lowest_task_id = task_id_bid
    #
    #     if smallest_bid != np.inf:
    #         return task_id_bid, smallest_bid
    #
    # '''
    # Create bid_msg and send it to the auctioneer
    # '''
    # def send_bid(self, n_round, task_id, bid):
    #     # Create bid message
    #     bid_msg = dict()
    #     bid_msg['header'] = dict()
    #     bid_msg['payload'] = dict()
    #     bid_msg['header']['type'] = 'BID'
    #     bid_msg['header']['metamodel'] = 'ropod-msg-schema.json'
    #     bid_msg['header']['msgId'] = str(uuid.uuid4())
    #     bid_msg['header']['timestamp'] = int(round(time.time()) * 1000)
    #
    #     bid_msg['payload']['metamodel'] = 'ropod-bid-schema.json'
    #     bid_msg['payload']['robot_id'] = self.id
    #     bid_msg['payload']['n_round'] = n_round
    #     bid_msg['payload']['task_id'] = task_id
    #     bid_msg['payload']['bid'] = bid['bid']
    #
    #     # self.makespan_round = self.compute_makespan()
    #     # self.completion_time_round = self.compute_completion_time()
    #     # self.idle_time = self.compute_idle_time()
    #     # self.travel_cost_round = self.compute_travel_cost(bid['scheduled_tasks'])
    #
    #     self.bid_round = bid['bid']
    #     self.scheduled_tasks_round = bid['scheduled_tasks']
    #     # self.minimal_stn_round = bid['stn']
    #     self.number_bids += 1
    #
    #     tasks = [task.id for task in self.scheduled_tasks_round]
    #
    #     self.verboseprint("[INFO] Round {}: Robod_id {} bids {} for task {} and scheduled_tasks {}".format(n_round, self.id, self.bid_round, task_id, tasks))
    #
    #     self.whisper(bid_msg, peer='auctioneer_' + self.method)
    #
    # '''
    # Create empty_bid_msg for each task in empty_bids and send it to the auctioneer
    # '''
    # def send_empty_bid(self, n_round, empty_bids):
    #     empty_bid_msg = dict()
    #     empty_bid_msg['header'] = dict()
    #     empty_bid_msg['payload'] = dict()
    #     empty_bid_msg['header']['type'] = 'EMPTY-BID'
    #     empty_bid_msg['header']['metamodel'] = 'ropod-msg-schema.json'
    #     empty_bid_msg['header']['msgId'] = str(uuid.uuid4())
    #     empty_bid_msg['header']['timestamp'] = int(round(time.time()) * 1000)
    #
    #     empty_bid_msg['payload']['metamodel'] = 'ropod-bid-schema.json'
    #     empty_bid_msg['payload']['robot_id'] = self.id
    #     empty_bid_msg['payload']['n_round'] = n_round
    #     empty_bid_msg['payload']['task_ids'] = list()
    #
    #     for task_id in empty_bids:
    #         empty_bid_msg['payload']['task_ids'].append(task_id)
    #
    #     self.verboseprint("[INFO] Round {}: Robot id {} sends empty bid for tasks {}".format(n_round, self.id, empty_bids))
    #
    #     self.whisper(empty_bid_msg, peer='auctioneer_' + self.method)
    #
    # def allocate_to_robot(self, task_id):
    #     # Update the schedule and stn with the values bid
    #     self.scheduled_tasks = copy.deepcopy(self.scheduled_tasks_round)
    #     self.minimal_stn = copy.deepcopy(self.minimal_stn_round)
    #
    #     # Get the Task object of the task to be allocated and add it
    #     # to the list of allocated_tasks
    #     for task in self.received_tasks_round:
    #         if task.id == task_id:
    #             n_previously_allocated_tasks = len(self.order_allocation)
    #             self.order_allocation[task_id] = n_previously_allocated_tasks
    #
    #     self.verboseprint("[INFO] Robot {} allocated task {}".format(self.id, task_id))
    #
    #     tasks = [task.id for task in self.scheduled_tasks]
    #     self.verboseprint("[INFO] Tasks scheduled to robot {}:{}".format(self.id, tasks))
    #
    #     #Update the travel cost and the makespan
    #     # self.distance_robot = self.travel_cost_round
    #     # self.makespan = self.makespan_round
    #
    #     # if self.bidding_rule == 'tessiduo':
    #     #     # Update the travel cost and the makespan
    #     #     self.distance_robot = self.travel_cost_round
    #     #     self.makespan = self.makespan_round
    #     #     self.verboseprint("[INFO] Robot {} current travel cost {}".format(self.id, self.distance_robot))
    #     #
    #     #     self.verboseprint("[INFO] Robot {} current makespan {}".format(self.id, self.makespan))
    #
    #     # print("---------------------------------------")
    #     # self.update_time_schedule()
    #     # print("---------------------------------------")
    #
    #     self.send_schedule()
    #
    # ''' Sends the updated schedule of the robot to the auctioneer.
    # '''
    # def send_schedule(self):
    #     self.distance = self.compute_distance(self.scheduled_tasks)
    #     if self.bidding_rule == self.IDLE_TIME:
    #         self.idle_time += self.bid_round
    #
    #     schedule_msg = dict()
    #     schedule_msg['header'] = dict()
    #     schedule_msg['payload'] = dict()
    #     schedule_msg['header']['type'] = 'SCHEDULE'
    #     schedule_msg['header']['metamodel'] = 'ropod-msg-schema.json'
    #     schedule_msg['header']['msgId'] = str(uuid.uuid4())
    #     schedule_msg['header']['timestamp'] = int(round(time.time()) * 1000)
    #     schedule_msg['payload']['metamodel'] = 'ropod-msg-schema.json'
    #     schedule_msg['payload']['robot_id'] = self.id
    #     schedule_msg['payload']['allocated_tasks'] = self.order_allocation
    #     # schedule_msg['payload']['bid'] = self.bid_round
    #     schedule_msg['payload']['schedule'] = list()
    #     for i, task in enumerate(self.scheduled_tasks):
    #         schedule_msg['payload']['schedule'].append(task.to_dict())
    #     # schedule_msg['payload']['makespan'] = self.makespan
    #     # schedule_msg['payload']['completion_time'] = self.completion_time
    #     # schedule_msg['payload']['idle_time'] = self.idle_time
    #     # schedule_msg['payload']['distance_robot'] = self.travel_cost
    #     # if self.bidding_rule == 'tessiduo':
    #     #     schedule_msg['payload']['makespan'] = self.makespan
    #     #     schedule_msg['payload']['distance_robot'] = self.distance_robot
    #     # else:
    #     #     schedule_msg['payload']['makespan'] = self.bid_round
    #
    #     # self.update_time_schedule(self.minimal_stn)
    #
    #
    #     # time_schedule = self.get_time_schedule()
    #     # schedule_msg['payload']['time_schedule'] = time_schedule
    #
    #     self.verboseprint("[INFO] Robot sends its updated schedule to the auctioneer.")
    #
    #     self.whisper(schedule_msg, peer='auctioneer_' + self.method)
    #
    # def reset_variables(self):
    #     self.scheduled_tasks = list()
    #     self.minimal_stn = list()
    #     self.order_allocation = dict()
    #     self.number_bids = 0
    #     self.position = self.initial_position
    #     self.distance = 0
    #     self.idle_time = 0
    #
    #     self.verboseprint("[INFO] Robot {} changed position to {}".format(self.id, self.position.name))
    #     self.send_new_robot_position()
    #
    #     self.verboseprint("[INFO] Robot {} reset its variables".format(self.id))
    #
    # def clean_schedule(self):
    #     if self.scheduled_tasks:
    #         last_task = self.scheduled_tasks.pop()
    #         self.position = last_task.delivery_pose
    #         self.scheduled_tasks = list()
    #         self.minimal_stn = list()
    #         self.order_allocation = dict()
    #
    #         self.distance = 0.
    #         self.idle_time = 0.
    #
    #         self.verboseprint("[INFO] Robot {} cleared its schedule".format(self.id))
    #         self.verboseprint("[INFO] Robot: {} changed position to: {} ".format(self.id, self.position.name))
    #         self.send_new_robot_position()
    #     else:
    #         self.verboseprint("[INFO] Robot {} had no scheduled tasks".format(self.id))
    #
    # ''' Sends the new robot position to the auctioneer
    # '''
    # def send_new_robot_position(self):
    #     position_msg = dict()
    #     position_msg['header'] = dict()
    #     position_msg['payload'] = dict()
    #     position_msg['header']['type'] = 'ROBOT-POSITION'
    #     position_msg['header']['metamodel'] = 'ropod-msg-schema.json'
    #     position_msg['header']['msgId'] = str(uuid.uuid4())
    #     position_msg['header']['timestamp'] = int(round(time.time()) * 1000)
    #
    #     position_msg['payload']['metamodel'] = 'ropod-msg-schema.json'
    #     position_msg['payload']['robot_id'] = self.id
    #     position_msg['payload']['position'] = self.position.name
    #
    #     self.verboseprint("[INFO] Robot sends its new position to the auctioneer.")
    #
    #     self.whisper(position_msg, peer='auctioneer_' + self.method)
    #
    # # '''
    # # Returns a dictionary with the start and finish times of all tasks in the STN
    # # times[position_in_schedule]['start_time']
    # # times[position_in_schedule]['finish_time']
    # # '''
    # # def get_time_schedule(self):
    # #     n_vertices = len(self.minimal_stn)
    # #     times = dict()
    # #     first_column = list()
    # #
    # #     # Get the first column of the minimal_stn
    # #     for i in range(0, n_vertices):
    # #         first_column.append(self.minimal_stn[i][0])
    # #
    # #     # Remove first element of the list
    # #     first_column.pop(0)
    # #
    # #     e_s_times = [first_column[i] for i in range(0, len(first_column)) if int(i) % 2 == 0]
    # #     e_f_times = [first_column[i] for i in range(0, len(first_column)) if int(i) % 2 != 0]
    # #
    # #     for i in range(0, len(e_s_times)):
    # #         times[i] = dict()
    # #         times[i]['start_time'] = - round(e_s_times[i], 2)
    # #         times[i]['finish_time'] = - round(e_f_times[i], 2)
    # #
    # #     return times
    #
    # ''' Updates the start time (time at which the task will be dispatched)
    #     and finish time of scheduled tasks
    #     Returns the earliest start time (time at which the robot will be at the task pickup location
    # '''
    # def update_time_schedule(self, minimal_stn):
    #     # Add option to update est
    #     n_vertices = len(minimal_stn)
    #     first_column = list()  # Contains earliest start and finish times
    #     first_row = list()  # Contains latest start and finish times
    #
    #     # print("Minimial stn: ", self.minimal_stn)
    #
    #     # Get the first column of the minimal_stn
    #     for i in range(0, n_vertices):
    #         first_column.append(minimal_stn[i][0])
    #         first_row.append(minimal_stn[0][i])
    #
    #     # Remove first element of the list
    #     first_column.pop(0)
    #     first_row.pop(0)
    #
    #     e_s_times = [first_column[i] for i in range(0, len(first_column)) if int(i) % 2 == 0]
    #     e_f_times = [first_column[i] for i in range(0, len(first_column)) if int(i) % 2 != 0]
    #
    #     l_s_times = [first_row[i] for i in range(0, len(first_row)) if int(i) % 2 == 0]
    #     l_f_times = [first_row[i] for i in range(0, len(first_row)) if int(i) % 2 != 0]
    #
    #     for i, task in enumerate(self.scheduled_tasks):
    #         # print("Task id: ", task.id)
    #         # e_s_t = -round(e_s_times[i], 2)
    #         # e_f_t = -round(e_f_times[i], 2)
    #         # l_s_t = round(l_s_times[i], 2)
    #         # l_f_t = round(l_f_times[i], 2)
    #
    #         e_s_t = -e_s_times[i]
    #         e_f_t = -e_f_times[i]
    #         l_s_t = l_s_times[i]
    #         l_f_t = l_f_times[i]
    #
    #
    #         if i == 0:  # First task in the schedule
    #             travel_time = self.get_distance(self.position, task.pickup_pose)
    #             # print("Travel time from current position {} to {}: {}".format(self.position.name, task.id, travel_time))
    #
    #         elif i < len(self.scheduled_tasks):
    #             previous_task = self.scheduled_tasks[i-1]
    #             travel_time = self.get_travel_time(previous_task.delivery_pose, task.pickup_pose)
    #             # print("Travel time from {} to {}: {} ".format(previous_task.id, task.id, travel_time))
    #
    #         task.start_time = round(e_s_t - travel_time, 2)
    #         task.finish_time = round(e_f_t, 2)
    #         task.pickup_start_time = round(e_s_t, 2)
    #
    #         # print("est: ", e_s_t)
    #         # print("eft: ", e_f_t)
    #         # print("lst: ", l_s_t)
    #         # print("lft: ", l_f_t)
    #         # print("st: ", task.start_time)
    #         # print("ft: ", task.finish_time)
    #


if __name__ == '__main__':
    code_dir = os.path.abspath(os.path.dirname(__file__))
    main_dir = os.path.dirname(code_dir)

    config_params = ConfigFileReader.load("../config/config.yaml")

    parser = argparse.ArgumentParser()
    parser.add_argument('ropod_id', type=str, help='example: ropod_001')
    args = parser.parse_args()
    ropod_id = args.ropod_id

    with open('../config/logging.yaml', 'r') as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)


    # time.sleep(5)

    robot = Robot(ropod_id, config_params)
    robot.start()

    try:
        while True:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        # logging.info("Terminating %s proxy ...", ropod_id)
        robot.shutdown()
        # logging.info("Exiting...")
        print("Exiting")
