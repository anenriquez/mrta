import copy
import logging

from fmlib.models.robot import Robot
from pymodm.errors import DoesNotExist
from ropod.structs.task import TaskStatus as TaskStatusConst
from ropod.utils.uuid import generate_uuid
from stn.exceptions.stp import NoSTPSolution

from mrs.allocation.bidding_rule import BiddingRule
from mrs.db.models.actions import GoTo
from mrs.db.models.task import InterTimepointConstraint
from mrs.db.models.task import Task
from mrs.exceptions.allocation import TaskNotFound
from mrs.messages.bid import NoBid
from mrs.messages.task_announcement import TaskAnnouncement
from mrs.messages.task_contract import TaskContract, TaskContractAcknowledgment, AllocationInfo

""" Implements a variation of the the TeSSI algorithm using the bidding_rule
specified in the config file
"""


class Bidder:

    def __init__(self, robot_id, stp_solver, timetable, bidding_rule, auctioneer_name, **kwargs):
        """
        Includes bidder functionality for a robot in a multi-robot task-allocation auction-based
        approach

        Args:

            robot_id (str): id of the robot, e.g. robot_001
            stp_solver (STP): Simple Temporal Problem object
            bidding_rule(dict): robustness and temporal criteria for the bidding rule
            auctioneer_name (str): name of the auctioneer pyre node
            kwargs:
                api (API): object that provides middleware functionality
                robot_store (robot_store): interface to interact with the db

        """
        self.robot_id = robot_id
        self.stp_solver = stp_solver
        self.timetable = timetable
        self.timetable.fetch()
        self.api = kwargs.get('api')
        self.robot_store = kwargs.get('robot_store')
        self.planner = kwargs.get('planner')

        self.logger = logging.getLogger('mrs.bidder.%s' % self.robot_id)

        self.bidding_rule = BiddingRule(bidding_rule, timetable)
        self.auctioneer_name = auctioneer_name
        self.bid_placed = None
        self.changed_timetable = False

        self.logger.debug("Bidder initialized %s", self.robot_id)

    def configure(self, **kwargs):
        api = kwargs.get('api')
        robot_store = kwargs.get('robot_store')
        if api:
            self.api = api
        if robot_store:
            self.robot_store = robot_store

    def task_announcement_cb(self, msg):
        payload = msg['payload']
        task_announcement = TaskAnnouncement.from_payload(payload)
        self.logger.debug("Received TASK-ANNOUNCEMENT msg round %s", task_announcement.round_id)
        self.logger.debug("Current stn: %s", self.timetable.stn)
        self.logger.debug("Current dispatchable graph: %s", self.timetable.dispatchable_graph)
        self.compute_bids(task_announcement)

    def task_contract_cb(self, msg):
        payload = msg['payload']
        task_contract = TaskContract.from_payload(payload)

        if task_contract.robot_id == self.robot_id:
            self.logger.debug("Robot %s received TASK-CONTRACT", self.robot_id)

            if not self.changed_timetable:
                self.allocate_to_robot(task_contract.task_id)
                self.send_contract_acknowledgement(task_contract, accept=True)
            else:
                self.logger.warning("The timetable changed before the round was completed, "
                                    "as a result, the bid placed %s is no longer valid ",
                                    self.bid_placed)
                self.send_contract_acknowledgement(task_contract, accept=False)

    def compute_bids(self, task_announcement):
        bids = list()
        no_bids = list()
        round_id = task_announcement.round_id
        self.changed_timetable = False
        self.bid_placed = None

        for task in task_announcement.tasks:
            self.logger.debug("Computing bid of task %s", task.task_id)
            best_bid = self.compute_bid(task, round_id)

            if best_bid:
                self.logger.debug("Best bid %s", best_bid)
                bids.append(best_bid)
            else:
                self.logger.warning("No bid for task %s", task.task_id)
                no_bid = NoBid(task.task_id, self.robot_id, round_id)
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
            self.logger.debug("Placing bid %s ", self.bid_placed)
            self.send_bid(bid)

        if no_bids:
            for no_bid in no_bids:
                self.logger.debug("Sending no bid for task %s", no_bid.task_id)
                self.send_bid(no_bid)

    def compute_bid(self, task, round_id):
        best_bid = None
        n_tasks = len(self.timetable.get_tasks())

        # Insert task in each possible insertion_point of the stn
        # Add from insertion_point 1 onwards (insertion_point 0 is reserved for the ztp)
        for insertion_point in range(1, n_tasks+2):
            stn_tasks = list()
            pre_task_actions = list()
            prev_version_next_task = None

            self.logger.debug("Computing bid for task %s in insertion_point %s", task.task_id, insertion_point)
            if not self.insert_in(insertion_point):
                continue

            prev_location = self.get_previous_location(insertion_point)
            pre_task_actions.append(self.get_pre_task_action(task, prev_location))

            stn_task = self.timetable.to_stn_task(task, insertion_point)
            self.timetable.insert_task(stn_task, insertion_point)
            stn_tasks.append(stn_task)

            try:
                # Update previous location and start constraints of next task (if any)
                next_task = self.timetable.get_task(insertion_point+1)
                prev_version_next_task = self.timetable.get_stn_task(next_task.task_id)

                prev_location = task.request.delivery_location
                pre_task_actions.append(self.get_pre_task_action(next_task, prev_location))

                stn_task = self.timetable.update_stn_task(next_task, insertion_point+1)
                self.timetable.update_task(stn_task)
                stn_tasks.append(stn_task)
            except TaskNotFound as e:
                pass

            allocation_info = AllocationInfo(insertion_point, copy.deepcopy(stn_tasks), pre_task_actions)
            stn = copy.deepcopy(self.timetable.stn)

            try:
                bid = self.bidding_rule.compute_bid(stn, self.robot_id, round_id, task, allocation_info)

                self.logger.debug("Bid: %s", bid)

                if best_bid is None or \
                        bid < best_bid or \
                        (bid == best_bid and bid.task_id < best_bid.task_id):
                    best_bid = bid

            except NoSTPSolution:
                self.logger.debug("The STN is inconsistent with task %s in insertion_point %s", task.task_id, insertion_point)

            self.timetable.stn.remove_task(insertion_point)

            if prev_version_next_task is not None:
                self.timetable.stn.update_task(prev_version_next_task)

        return best_bid

    def insert_in(self, insertion_point):
        try:
            task = self.timetable.get_task(insertion_point)
            if task.frozen:
                self.logger.debug("Task %s is frozen. "
                                  "Not computing bid for this insertion point %s", task.task_id, insertion_point)
                return False
            return True
        except TaskNotFound as e:
            return True

    def get_previous_location(self, insertion_point):
        if insertion_point == 1:
            previous_location = self.get_robot_location()
        else:
            previous_task = self.timetable.get_task(insertion_point - 1)
            previous_location = previous_task.request.delivery_location

        self.logger.debug("Previous location: %s ", previous_location)
        return previous_location

    def get_robot_location(self):
        try:
            position = Robot.get_robot(self.robot_id).position
            robot_location = self.planner.get_node(position.x, position.y, position.theta)
        except DoesNotExist:
            self.logger.warning("No information about robot's location")
            robot_location = "AMK_D_L-1_C39"
        return robot_location

    def get_pre_task_action(self, task, previous_location):
        travel_path = self.get_travel_path(previous_location, task.request.pickup_location)
        travel_time = self.get_travel_time(travel_path)
        task.update_inter_timepoint_constraint(**travel_time.to_dict())

        pre_task_action = GoTo(action_id=generate_uuid(),
                               type="ROBOT-TO-PICKUP",
                               locations=travel_path,
                               task_id=task.task_id,
                               estimated_duration=travel_time)
        return pre_task_action

    def get_travel_path(self, robot_position, pickup_location):
        if self.planner:
            return self.planner.get_path(robot_position, pickup_location)

    def get_travel_time(self, path):
        if path:
            mean, variance = self.planner.get_estimated_duration(path)
        else:  # temporal hack
            mean = 1
            variance = 0.1

        travel_time = InterTimepointConstraint(name="travel_time", mean=mean, variance=variance)
        self.logger.debug("Travel time: %s", travel_time)
        return travel_time

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

        return smallest_bid

    def send_bid(self, bid):
        """ Creates bid_msg and sends it to the auctioneer
        """
        msg = self.api.create_message(bid)

        self.api.publish(msg, peer=self.auctioneer_name)

    def allocate_to_robot(self, task_id):
        allocation_info = self.bid_placed.get_allocation_info()
        for stn_task in allocation_info.stn_tasks:
            self.timetable.add_stn_task(stn_task)

        self.timetable.stn = allocation_info.stn
        self.timetable.dispatchable_graph = allocation_info.dispatchable_graph
        self.timetable.store()

        self.logger.debug("Robot %s allocated task %s", self.robot_id, task_id)
        self.logger.debug("STN: \n %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph: \n %s", self.timetable.dispatchable_graph)

        tasks = [task for task in self.timetable.get_tasks()]

        self.logger.debug("Tasks allocated to robot %s:%s", self.robot_id, tasks)
        task = Task.get_task(task_id)
        task.update_status(TaskStatusConst.ALLOCATED)
        task.assign_robots([self.robot_id])

    def task_contract_acknowledgement_cb(self, msg):
        payload = msg['payload']
        ack = TaskContractAcknowledgment.from_payload(payload)
        if not ack.accept:
            self.logger.warning("Undoing allocation of task %s", ack.task_id)
            self.timetable.remove_task(ack.task_id)
            for stn_task in ack.allocation_info.stn_tasks:
                if stn_task.task_id != ack.task_id:
                    self.timetable.update_task(stn_task)

        tasks = [task for task in self.timetable.get_tasks()]

        self.logger.debug("Tasks allocated to robot %s:%s", self.robot_id, tasks)
        self.logger.debug("STN: \n %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph: \n %s", self.timetable.dispatchable_graph)

    def send_contract_acknowledgement(self, task_contract, accept=True):
        allocation_info = self.bid_placed.get_allocation_info()
        task_contract_acknowledgement = TaskContractAcknowledgment(task_contract.task_id,
                                                                   task_contract.robot_id,
                                                                   allocation_info,
                                                                   accept)
        msg = self.api.create_message(task_contract_acknowledgement)

        self.logger.debug("Robot %s sends task-contract-acknowledgement msg ", self.robot_id)
        self.api.publish(msg, groups=['TASK-ALLOCATION'])
