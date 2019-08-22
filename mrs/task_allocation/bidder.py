import copy
import logging

from mrs.exceptions.task_allocation import NoSTPSolution
from mrs.structs.allocation import FinishRound
from mrs.structs.bid import Bid
from mrs.structs.task import TaskStatus
from mrs.task_allocation.bidding_rule import BiddingRule
from mrs.robot_base import RobotBase
import numpy as np

""" Implements a variation of the the TeSSI algorithm using the bidding_rule 
specified in the config file
"""


class Bidder(RobotBase):

    def __init__(self, robot_config, bidder_config):
        super().__init__(**robot_config)
        self.logger = logging.getLogger('mrs.bidder.%s' % self.id)

        robustness = bidder_config.get('bidding_rule').get('robustness')
        temporal = bidder_config.get('bidding_rule').get('temporal')
        self.bidding_rule = BiddingRule(robustness, temporal)

        self.auctioneer_name = bidder_config.get("auctioneer_name")
        self.bid_placed = Bid()

        self.logger.debug("Bidder initialized %s", self.id)

    def task_announcement_cb(self, msg):
        self.logger.debug("Robot %s received TASK-ANNOUNCEMENT", self.id)
        round_id = msg['payload']['round_id']
        received_tasks = msg['payload']['tasks']
        self.timetable = self.db_interface.get_timetable(self.id, self.stp)
        self.compute_bids(received_tasks, round_id)

    def allocation_cb(self, msg):
        self.logger.debug("Robot %s received ALLOCATION", self.id)
        task_id = msg['payload']['task_id']
        winner_id = msg['payload']['robot_id']

        if winner_id == self.id:
            self.allocate_to_robot(task_id)
            self.send_finish_round()

    def compute_bids(self, received_tasks, round_id):
        bids = list()
        no_bids = list()

        for task_id, task_info in received_tasks.items():
            task = self.task_cls.from_dict(task_info)
            self.db_interface.update_task(task)
            self.logger.debug("Computing bid of task %s", task.id)

            # Insert task in each possible position of the stn and
            # get the best_bid for each task
            best_bid = self.insert_task(task, round_id)

            if best_bid.cost != (np.inf, np.inf):
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
        if bid:
            self.logger.debug("Robot %s placed bid %s", self.id, self.bid_placed)
            self.send_bid(bid)

        if no_bids:
            for no_bid in no_bids:
                self.logger.debug("Sending no bid for task %s", no_bid.task_id)
                self.send_bid(no_bid)

    def insert_task(self, task, round_id):
        best_bid = Bid(self.id, round_id, task.id)

        tasks = self.timetable.get_tasks()
        if tasks:
            n_tasks = len(tasks)
        else:
            n_tasks = 0

        # Add task to the STN from position 1 onwards (position 0 is reserved for the zero_timepoint)
        for position in range(1, n_tasks+2):
            # TODO check if the robot can make it to the task, if not, return

            self.logger.debug("Schedule: %s", self.timetable.schedule)
            if position == 1 and self.timetable.is_scheduled():
                self.logger.debug("Not adding task in position %s", position)
                continue

            self.logger.debug("Computing bid for task %s in position %s", task.id, position)

            try:
                bid = self.bidding_rule.compute_bid(self.id, round_id, task, position, self.timetable)

                self.logger.debug("Bid: (%s, %s)", bid.risk_metric, bid.temporal_metric)

                if bid < best_bid or (bid == best_bid and bid.task_id < best_bid.task_id):
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
            if bid < smallest_bid or (bid == smallest_bid and bid.task_id < smallest_bid.task_id):
                smallest_bid = copy.deepcopy(bid)

        if smallest_bid.cost == (np.inf, np.inf):
            return None

        return smallest_bid

    def send_bid(self, bid):
        """ Creates bid_msg and sends it to the auctioneer_name

        :param bid:
        :param round_id:
        :return:
        """
        msg = self.api.create_message(bid)
        tasks = [task for task in bid.timetable.get_tasks()]

        self.logger.info("Round %s: robod_id %s bids %s for task %s and tasks %s", bid.round_id, self.id, bid.cost, bid.task_id, tasks)
        self.api.publish(msg, peer=self.auctioneer_name)

    def allocate_to_robot(self, task_id):

        self.timetable = copy.deepcopy(self.bid_placed.timetable)
        self.db_interface.update_timetable(self.timetable)
        task_dict = self.db_interface.get_task(task_id)
        task = self.task_cls.from_dict(task_dict)
        self.db_interface.update_task_status(task, TaskStatus.ALLOCATED)

        self.logger.info("Robot %s allocated task %s", self.id, task_id)
        self.logger.debug("STN %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph %s", self.timetable.dispatchable_graph)

        tasks = [task for task in self.timetable.get_tasks()]

        self.logger.debug("Tasks allocated to robot %s:%s", self.id, tasks)

    def send_finish_round(self):
        finish_round = FinishRound(self.id)
        msg = self.api.create_message(finish_round)

        self.logger.info("Robot %s sends close round msg ", self.id)
        self.api.publish(msg, groups=['TASK-ALLOCATION'])

