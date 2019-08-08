import copy
import uuid
import time
import argparse
import logging.config

from stn.stp import STP
from mrs.task_allocation.bid import Bid
from mrs.task_allocation.bidding_rule import BiddingRule
from mrs.task_allocation.timetable import Timetable
from mrs.exceptions.task_allocation import NoSTPSolution

""" Implements a variation of the the TeSSI algorithm using the bidding_rule 
specified in the config file
"""


class Bidder(object):

    def __init__(self, robot_id, ccu_store, api, task_cls, bidding_rule, allocation_method, auctioneer, **kwargs):

        self.id = robot_id
        self.ccu_store = ccu_store

        self.api = api
        self.api.register_callback(self.task_announcement_cb, 'TASK-ANNOUNCEMENT')
        self.api.register_callback(self.allocation_cb, 'ALLOCATION')
        self.api.register_callback(self.task_cb, 'TASK')

        robustness = bidding_rule.get('robustness')
        temporal = bidding_rule.get('temporal')
        self.bidding_rule = BiddingRule(robustness, temporal)

        self.task_cls = task_cls
        self.allocation_method = allocation_method
        self.auctioneer = auctioneer

        self.logger = logging.getLogger('mrs.robot.%s' % self.id)
        self.logger.debug("Starting robot %s", self.id)

        # TODO: Read timetable from db
        stp = STP(robustness)
        self.timetable = Timetable(stp, robot_id)

        self.bid_placed = Bid()

    def __str__(self):
        to_print = ""
        to_print += "Robot {}".format(self.id)
        to_print += '\n'
        to_print += "Groups {}".format(self.api.groups())
        return to_print

    def task_announcement_cb(self, msg):
        self.logger.debug("Robot %s received TASK-ANNOUNCEMENT", self.id)
        round_id = msg['payload']['round_id']
        received_tasks = msg['payload']['tasks']
        self.compute_bids(received_tasks, round_id)

    def allocation_cb(self, msg):
        self.logger.debug("Robot %s received ALLOCATION", self.id)
        task_id = msg['payload']['task_id']
        winner_id = msg['payload']['winner_id']

        if winner_id == self.id:
            self.allocate_to_robot(task_id)
            self.send_finish_round()

    def task_cb(self, msg):
        self.logger.debug("Received task message")

    def compute_bids(self, received_tasks, round_id):
        bids = list()
        no_bids = list()

        for task_id, task_info in received_tasks.items():
            task = self.task_cls.from_dict(task_info)
            self.logger.debug("Computing bid of task %s", task.id)

            # Insert task in each possible position of the stn and
            # get the best_bid for each task
            best_bid = self.insert_task(task, round_id)

            if best_bid.cost != float('inf'):
                bids.append(best_bid)
            else:
                self.logger.debug("No bid for task %s", task.id)
                no_bids.append(best_bid)

        smallest_bid = self.get_smallest_bid(bids)
        self.bid_placed = copy.deepcopy(smallest_bid)

        self.send_bids(smallest_bid, no_bids)

    def send_bids(self, bid, no_bids):
        """ Sends the bid with the smallest cost
        Sends a no-bid per task that could not be accommodated in the stn

        :param bid: bid with the smallest cost
        :param no_bids: list of no bids
        """
        self.logger.debug("Robot %s placed bid %s", self.id, self.bid_placed)
        self.send_bid(bid)

        if no_bids:
            for no_bid in no_bids:
                self.logger.debug("Sending no bid for task %s", no_bid.task.id)
                self.send_bid(no_bid)

    def insert_task(self, task, round_id):
        best_bid = Bid(self.bidding_rule, self.id, round_id, task, self.timetable)

        tasks = self.timetable.get_tasks()
        n_tasks = len(tasks)

        # Add task to the STN from position 1 onwards (position 0 is reserved for the zero_timepoint)
        for i in range(0, n_tasks + 1):
            # TODO check if the robot can make it to the task, if not, return
            position = i+1

            self.timetable.add_task_to_stn(task, position)

            try:
                self.timetable.solve_stp()

                self.logger.debug("STN %s: ", self.timetable.stn)
                self.logger.debug("Dispatchable graph %s: ", self.timetable.dispatchable_graph)
                self.logger.debug("Robustness Metric %s: ", self.timetable.robustness_metric)

                bid = Bid(self.bidding_rule, self.id, round_id, task, self.timetable)
                bid.compute_cost(position)

                if bid < best_bid or (bid == best_bid and bid.task.id < best_bid.task.id):
                    best_bid = copy.deepcopy(bid)

            except NoSTPSolution:
                self.logger.exception("The stp solver could not solve the problem for"
                                      " task %s in position %s", task.id, position)

            # Restore schedule for the next iteration
            self.timetable.remove_task_from_stn(position)

        self.logger.debug("Best bid for task %s: %s", task.id, best_bid)

        return best_bid

    @staticmethod
    def get_smallest_bid(bids):
        """ Get the bid with the smallest cost among all bids.

        :param bids: list of bids
        :return: the bid with the smallest cost
        """
        smallest_bid = Bid()

        for bid in bids:
            if bid < smallest_bid or (bid == smallest_bid and bid.task.id < smallest_bid.task.id):
                smallest_bid = copy.deepcopy(bid)

        if smallest_bid.cost == float('inf'):
            return None

        return smallest_bid

    def send_bid(self, bid):
        """ Creates bid_msg and sends it to the auctioneer

        :param bid:
        :param round_id:
        :return:
        """
        self.logger.debug("Bid %s", bid.msg.to_dict())

        bid_msg = dict()
        bid_msg['header'] = dict()
        bid_msg['payload'] = dict()
        bid_msg['header']['type'] = 'BID'
        bid_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        bid_msg['header']['msgId'] = str(uuid.uuid4())
        bid_msg['header']['timestamp'] = int(round(time.time()) * 1000)

        bid_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'
        bid_msg['payload']['bid'] = bid.msg.to_dict()

        tasks = [task for task in bid.timetable.get_tasks()]

        self.logger.info("Round %s: robod_id %s bids %s for task %s and tasks %s", bid.round_id, self.id, bid.cost, bid.task.id, tasks)
        self.api.whisper(bid_msg, peer=self.auctioneer)

    def allocate_to_robot(self, task_id):

        # Update the timetable
        self.timetable = copy.deepcopy(self.bid_placed.timetable)

        self.logger.info("Robot %s allocated task %s", self.id, task_id)
        self.logger.debug("STN %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph %s", self.timetable.dispatchable_graph)

        tasks = [task for task in self.timetable.get_tasks()]

        self.logger.debug("Tasks scheduled to robot %s:%s", self.id, tasks)

    def send_finish_round(self):
        close_msg = dict()
        close_msg['header'] = dict()
        close_msg['payload'] = dict()
        close_msg['header']['type'] = 'FINISH-ROUND'
        close_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        close_msg['header']['msgId'] = str(uuid.uuid4())
        close_msg['header']['timestamp'] = int(round(time.time()) * 1000)
        close_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'

        self.logger.info("Robot %s sends close round msg ", self.id)
        self.api.whisper(close_msg, peer=self.auctioneer)


# if __name__ == '__main__':
#
#     from fleet_management.config.loader import Config
#
#     config_file_path = '../config/config.yaml'
#     config = Config(config_file_path, initialize=False)
#     config.configure_logger()
#     ccu_store = config.configure_ccu_store()
#
#     parser = argparse.ArgumentParser()
#     parser.add_argument('robot_id', type=str, help='example: ropod_001')
#     args = parser.parse_args()
#     robot_id = args.robot_id
#
#     robot = config.configure_robot_proxy(robot_id, ccu_store)
#
#     time.sleep(5)
#
#     robot.api.start()
#
#     try:
#         while True:
#             robot.api.run()
#             time.sleep(0.5)
#     except (KeyboardInterrupt, SystemExit):
#         logging.info("Terminating %s proxy ...", robot_id)
#         robot.api.shutdown()
#         logging.info("Exiting...")

