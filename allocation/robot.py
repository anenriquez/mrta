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

        super().__init__(self.id, self.zyre_params.groups, self.zyre_params.message_types, acknowledge=False)

        self.logger = logging.getLogger('robot: %s' % robot_id)
        self.logger.debug("This is a debug message")

        self.stnu = STNU()
        self.scheduled_tasks = list()
        self.dataset_start_time = 0

    def reinitialize_auction_variables(self):
        self.received_tasks_round = list()
        self.bid_round = None
        self.scheduled_tasks_round = list()
        self.minimal_stn_round = list()

    def receive_msg_cb(self, msg_content):
        dict_msg = self.convert_zyre_msg_to_dict(msg_content)
        if dict_msg is None:
            return
        message_type = dict_msg['header']['type']

        if message_type == 'START':
            self.dataset_start_time = dict_msg['payload']['start_time']
            self.logger.debug("Received dataset start time %s", self.dataset_start_time)

        elif message_type == 'TASK-ANNOUNCEMENT':
            self.reinitialize_auction_variables()
            n_round = dict_msg['payload']['round']
            tasks = dict_msg['payload']['tasks']
            self.compute_bids(tasks, n_round)

    def compute_bids(self, tasks, n_round):
        bids = dict()
        empty_bids = list()

        for task_id, task_info in tasks.items():
            task = Task.from_dict(task_info)
            self.received_tasks_round.append(task)
            self.logger.debug("Computing bid of task %s", task.id)
            # Insert task in each possible position of the stnu
            self.insert_task(task)

    def insert_task(self, task):
        n_scheduled_tasks = len(self.scheduled_tasks)
        for i in range(0, n_scheduled_tasks + 1):
            self.scheduled_tasks.insert(i, task)
            # TODO check if the robot can make it to the first task in the schedule, if not, return
            self.stnu.build_stn(self.scheduled_tasks)
            print(self.stnu)
            minimal_stnu = self.stnu.floyd_warshall()
            if self.stnu.is_consistent(minimal_stnu):
                self.stnu.update_edges(minimal_stnu)
                self.stnu.update_time_schedule(minimal_stnu)
                completion_time = self.stnu.get_completion_time()
                print("Completion time: ", completion_time)

            # Restore new_schedule for the next iteration
            self.scheduled_tasks.pop(i)


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
