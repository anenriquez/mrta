import copy
import logging

from mrs.exceptions.allocation import NoSTPSolution
from mrs.robot_base import RobotBase
from mrs.allocation.allocation import FinishRound
from mrs.allocation.allocation import TaskAnnouncement, Allocation
from mrs.bidding.bid import Bid
from mrs.bidding.rule import BiddingRule
from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst


""" Implements a variation of the the TeSSI algorithm using the bidding_rule
specified in the config file
"""


class Bidder(RobotBase):

    def __init__(self, robot_id, stp_solver, bidding_rule, auctioneer_name, **kwargs):
        """
        Includes bidder functionality for a robot in a multi-robot task-allocation auction-based
        approach

        Args:

            robot_id (str): id of the robot, e.g. ropod_001
            stp_solver (STP): Simple Temporal Problem object
            bidding_rule(dict): robustness and temporal criteria for the bidding rule
            auctioneer_name (str): name of the auctioneer pyre node
            kwargs:
                api (API): object that provides middleware functionality
                robot_store (robot_store): interface to interact with the db

        """
        super().__init__(robot_id, stp_solver, **kwargs)
        self.logger = logging.getLogger('mrs.bidder.%s' % self.robot_id)

        robustness = bidding_rule.get('robustness')
        temporal = bidding_rule.get('temporal')
        self.bidding_rule = BiddingRule(robustness, temporal)

        self.auctioneer_name = auctioneer_name
        self.bid_placed = None

        self.experiment = kwargs.get('experiment')

        self.logger.debug("Bidder initialized %s", self.robot_id)

    def task_announcement_cb(self, msg):
        self.logger.debug("Robot %s received TASK-ANNOUNCEMENT", self.robot_id)
        payload = msg['payload']
        task_announcement = TaskAnnouncement.from_payload(payload)
        self.timetable = self.get_timetable()
        self.timetable.zero_timepoint = task_announcement.zero_timepoint
        self.compute_bids(task_announcement)

    def allocation_cb(self, msg):
        self.logger.debug("Robot %s received ALLOCATION", self.robot_id)
        payload = msg['payload']
        allocation = Allocation.from_payload(payload)

        if allocation.robot_id == self.robot_id:
            self.allocate_to_robot(allocation.task_id)
            self.send_finish_round()

    def compute_bids(self, task_announcement):
        bids = list()
        no_bids = list()
        round_id = task_announcement.round_id

        for task_lot in task_announcement.tasks_lots:
            self.logger.debug("Computing bid of task %s", task_lot.task.task_id)

            # Insert task in each possible position of the stn and
            # get the best_bid for each task
            best_bid = self.insert_task(task_lot, round_id)

            if best_bid:
                bids.append(best_bid)
            else:
                self.logger.debug("No bid for task %s", task_lot.task_id)
                no_bid = Bid(self.robot_id, round_id, task_lot.task.task_id)
                no_bids.append(no_bid)

        smallest_bid = self.get_smallest_bid(bids)

        self.send_bids(smallest_bid, no_bids)

    def send_bids(self, bid, no_bids):
        """ Sends the bid with the smallest cost
        Sends a no-bid per task that could not be accommodated in the stn

        :param bid: bid with the smallest cost
        :param no_bids: list of no bids
        """
        if bid:
            self.bid_placed = bid
            self.logger.debug("Robot %s placed bid (risk metric: %s, temporal metric: %s)", self.robot_id,
                              self.bid_placed.risk_metric, self.bid_placed.temporal_metric)
            self.send_bid(bid)

        if no_bids:
            for no_bid in no_bids:
                self.logger.debug("Sending no bid for task %s", no_bid.task_id)
                self.send_bid(no_bid)

    def insert_task(self, task_lot, round_id):
        best_bid = None

        n_tasks = len(self.timetable.get_tasks())

        # Add task to the STN from position 1 onwards (position 0 is reserved for the zero_timepoint)
        for position in range(1, n_tasks+2):
            # TODO check if the robot can make it to the task, if not, return

            self.logger.debug("Schedule: %s", self.timetable.schedule)
            if position == 1 and self.timetable.schedule:
                self.logger.debug("Not adding task in position %s", position)
                continue

            self.logger.debug("Computing bid for task %s in position %s", task_lot.task.task_id, position)

            try:
                bid = self.bidding_rule.compute_bid(self.robot_id, round_id, task_lot, position, self.timetable)

                self.logger.debug("Bid: (risk metric: %s, temporal metric: %s)", bid.risk_metric, bid.temporal_metric)

                if best_bid is None or \
                        bid < best_bid or\
                        (bid == best_bid and bid.task_id < best_bid.task_id):

                    best_bid = copy.deepcopy(bid)

            except NoSTPSolution:
                self.logger.warning("The stp solver could not solve the problem for"
                                    " task %s in position %s", task_lot.task.task_id, position)

            # Restore schedule for the next iteration
            self.timetable.remove_task_from_stn(position)

        self.logger.debug("Best bid for task %s: (risk metric: %s, temporal metric: %s)", task_lot.task.task_id,
                          best_bid.risk_metric, best_bid.temporal_metric)

        return best_bid

    @staticmethod
    def get_smallest_bid(bids):
        """ Get the bid with the smallest cost among all bids.

        :param bids: list of bids
        :return: the bid with the smallest cost
        """
        smallest_bid = None

        for bid in bids:
            if smallest_bid is None or\
                    bid < smallest_bid or\
                    (bid == smallest_bid and bid.task_id < smallest_bid.task_id):

                smallest_bid = copy.deepcopy(bid)

        if smallest_bid is None:
            return None

        return smallest_bid

    def send_bid(self, bid):
        """ Creates bid_msg and sends it to the auctioneer
        """
        msg = self.api.create_message(bid)

        self.api.publish(msg, peer=self.auctioneer_name)

    def allocate_to_robot(self, task_id):

        self.timetable = copy.deepcopy(self.bid_placed.timetable)
        self.timetable.store()

        self.logger.debug("Robot %s allocated task %s", self.robot_id, task_id)
        self.logger.debug("STN %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph %s", self.timetable.dispatchable_graph)

        tasks = [task for task in self.timetable.get_tasks()]

        self.logger.debug("Tasks allocated to robot %s:%s", self.robot_id, tasks)
        task = Task.get_task(task_id)
        task.update_status(TaskStatusConst.ALLOCATED)
        task.assign_robots([self.robot_id])

    def send_finish_round(self):
        finish_round = FinishRound(self.robot_id)
        msg = self.api.create_message(finish_round)

        self.logger.debug("Robot %s sends close round msg ", self.robot_id)
        self.api.publish(msg, groups=['TASK-ALLOCATION'])

