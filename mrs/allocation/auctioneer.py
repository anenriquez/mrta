import logging
from datetime import timedelta

from fmlib.models.tasks import TransportationTask as Task
from mrs.allocation.round import Round
from mrs.exceptions.allocation import AlternativeTimeSlot
from mrs.exceptions.allocation import InvalidAllocation
from mrs.exceptions.allocation import NoAllocation
from mrs.messages.bid import Bid, NoBid
from mrs.messages.task_announcement import TaskAnnouncement
from mrs.messages.task_contract import TaskContract, TaskContractAcknowledgment, TaskContractCancellation
from mrs.simulation.simulator import SimulatorInterface
from mrs.utils.time import to_timestamp
from ropod.structs.task import TaskStatus as TaskStatusConst
from ropod.utils.timestamp import TimeStamp

""" Implements a variation of the the TeSSI algorithm using the bidding_rule 
specified in the config file
"""


class Auctioneer(SimulatorInterface):

    def __init__(self, timetable_manager, closure_window=5, **kwargs):
        simulator = kwargs.get('simulator')
        super().__init__(simulator)

        self.logger = logging.getLogger("mrs.auctioneer")
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')
        self.robot_ids = list()
        self.timetable_manager = timetable_manager

        self.closure_window = timedelta(minutes=closure_window)
        self.alternative_timeslots = kwargs.get('alternative_timeslots', False)

        self.logger.debug("Auctioneer started")

        self.tasks_to_allocate = dict()
        self.allocated_tasks = dict()
        self.allocations = list()
        self.allocation_times = list()
        self.winning_bid = None
        self.changed_timetable = list()
        self.waiting_for_user_confirmation = list()
        self.round = Round(self.robot_ids, self.tasks_to_allocate)

    def configure(self, **kwargs):
        api = kwargs.get('api')
        ccu_store = kwargs.get('ccu_store')
        if api:
            self.api = api
        if ccu_store:
            self.ccu_store = ccu_store

    def register_robot(self, robot_id):
        self.logger.debug("Registering robot %s", robot_id)
        self.robot_ids.append(robot_id)
        self.timetable_manager.register_robot(robot_id)

    def set_ztp(self, time_):
        self.timetable_manager.ztp = time_

    def run(self):
        if self.tasks_to_allocate and self.round.finished:
            self.announce_tasks()

        if self.round.opened and self.round.time_to_close():
            try:
                round_result = self.round.get_result()
                self.process_round_result(round_result)

            except NoAllocation as e:
                self.logger.warning("No allocation made in round %s ", e.round_id)
                self.tasks_to_allocate = e.tasks_to_allocate
                self.finish_round()

            except AlternativeTimeSlot as e:
                self.process_alternative_timeslot(e)

    def process_round_result(self, round_result):
        self.winning_bid, self.tasks_to_allocate = round_result
        if self.winning_bid.earliest_start_time is None or\
                self.winning_bid.earliest_start_time and \
                self.is_valid_time(self.winning_bid.earliest_start_time.to_datetime()):
            self.send_task_contract(self.winning_bid.task_id, self.winning_bid.robot_id)
        else:
            self.logger.warning("The earliest start time of task %s is invalid", self.winning_bid.task_id)
            self.finish_round()

    def process_alternative_timeslot(self, exception):
        bid = exception.bid
        self.tasks_to_allocate = exception.tasks_to_allocate
        alternative_allocation = (bid.task_id, [bid.robot_id], bid.alternative_start_time)

        self.logger.debug("Alternative timeslot for task %s: robot %s, alternative start time: %s ", bid.task_id,
                          bid.robot_id, bid.alternative_start_time)

        self.waiting_for_user_confirmation.append(alternative_allocation)

        # TODO: Prompt the user to accept the alternative timeslot
        # For now, accept always
        self.winning_bid = bid
        self.send_task_contract(bid.task_id, bid.robot_id)

    def process_allocation(self):
        task = self.tasks_to_allocate.pop(self.winning_bid.task_id)
        try:
            self.timetable_manager.update_timetable(self.winning_bid.robot_id,
                                                    self.winning_bid.get_allocation_info(),
                                                    task)
        except InvalidAllocation as e:
            self.logger.warning("The allocation of task %s to robot %s is inconsistent. Aborting allocation."
                                "Task %s will be included in next allocation round", e.task_id, e.robot_id, e.task_id)
            self.undo_allocation(self.winning_bid.get_allocation_info())
            self.tasks_to_allocate[task.task_id] = task
            return

        self.allocated_tasks[task.task_id] = task

        allocation = (self.winning_bid.task_id, [self.winning_bid.robot_id])
        self.logger.debug("Allocation: %s", allocation)
        self.logger.debug("Tasks to allocate %s", [task_id for task_id, task in self.tasks_to_allocate.items()])

        self.logger.debug("Updating task status to ALLOCATED")

        self.allocations.append(allocation)
        self.allocation_times.append(self.round.time_to_allocate)
        self.finish_round()

    def undo_allocation(self, allocation_info):
        self.logger.warning("Undoing allocation of round %s", self.round.id)
        self.send_task_contract_cancellation(self.winning_bid.task_id,
                                             self.winning_bid.robot_id,
                                             allocation_info.prev_version_next_task)
        self.finish_round()

    def allocate(self, tasks):
        if isinstance(tasks, list):
            self.logger.debug("Auctioneer received a list of tasks")
            for task in tasks:
                self.tasks_to_allocate[task.task_id] = task
        else:
            self.logger.debug("Auctioneer received one task")
            self.tasks_to_allocate[tasks.task_id] = tasks
        self.logger.debug("Tasks to allocate %s", {task_id for (task_id, task) in self.tasks_to_allocate.items()})

    def finish_round(self):
        self.logger.debug("Finishing round %s", self.round.id)
        self.round.finish()

    def announce_tasks(self):
        tasks = list(self.tasks_to_allocate.values())
        earliest_task = Task.get_earliest_task(tasks)
        closure_time = earliest_task.pickup_constraint.earliest_time - self.closure_window

        if not self.is_valid_time(closure_time) and self.alternative_timeslots:
            # Closure window should be long enough to allow robots to bid (tune if necessary)
            closure_time = self.get_current_time() + self.closure_window

        elif not self.is_valid_time(closure_time) and not self.alternative_timeslots:
            self.logger.warning("Task %s cannot not be allocated at its given temporal constraints",
                                earliest_task.task_id)
            earliest_task.update_status(TaskStatusConst.PREEMPTED)
            self.tasks_to_allocate.pop(earliest_task.task_id)
            return

        self.changed_timetable.clear()
        for task in tasks:
            if not task.hard_constraints:
                self.update_soft_constraints(task)

        self.round = Round(self.robot_ids,
                           self.tasks_to_allocate,
                           n_tasks=len(tasks),
                           closure_time=closure_time,
                           alternative_timeslots=self.alternative_timeslots,
                           simulator=self.simulator)

        earliest_admissible_time = TimeStamp()
        earliest_admissible_time.timestamp = self.get_current_time() + timedelta(minutes=1)
        task_announcement = TaskAnnouncement(tasks, self.round.id, self.timetable_manager.ztp, earliest_admissible_time)

        self.logger.debug("Starting round: %s", self.round.id)
        self.logger.debug("Number of tasks to allocate: %s", len(tasks))

        msg = self.api.create_message(task_announcement)

        self.logger.debug("Auctioneer announces tasks %s", [task.task_id for task in tasks])

        self.round.start()
        self.api.publish(msg, groups=['TASK-ALLOCATION'])

    def update_soft_constraints(self, task):
        pickup_time_window = task.pickup_constraint.latest_time - task.pickup_constraint.earliest_time

        earliest_pickup_time = self.get_current_time() + timedelta(minutes=5)
        latest_pickup_time = earliest_pickup_time + pickup_time_window
        task.update_pickup_constraint(earliest_pickup_time, latest_pickup_time)

    def bid_cb(self, msg):
        payload = msg['payload']
        self.round.process_bid(payload, Bid)

    def no_bid_cb(self, msg):
        payload = msg['payload']
        self.round.process_bid(payload, NoBid)

    def task_contract_acknowledgement_cb(self, msg):
        payload = msg['payload']
        ack = TaskContractAcknowledgment.from_payload(payload)

        if ack.accept and ack.robot_id not in self.changed_timetable:
            self.logger.debug("Concluding allocation of task %s", ack.task_id)
            self.winning_bid.set_allocation_info(ack.allocation_info)
            self.process_allocation()

        elif ack.accept and ack.robot_id in self.changed_timetable:
            self.undo_allocation(ack.allocation_info)

        else:
            self.logger.warning("Round %s has to be repeated", self.round.id)
            self.finish_round()

    def send_task_contract_cancellation(self, task_id, robot_id, prev_version_next_task):
        task_contract_cancellation = TaskContractCancellation(task_id, robot_id, prev_version_next_task)
        msg = self.api.create_message(task_contract_cancellation)
        self.logger.debug("Cancelling contract for task %s", task_id)
        self.api.publish(msg, groups=['TASK-ALLOCATION'])

    def send_task_contract(self, task_id, robot_id):
        # Send TaskContract only if the timetable of robot_id has not changed since the round opened
        if robot_id not in self.changed_timetable:
            task_contract = TaskContract(task_id, robot_id)
            msg = self.api.create_message(task_contract)
            self.api.publish(msg, groups=['TASK-ALLOCATION'])
        else:
            self.logger.warning("Round %s has to be repeated", self.round.id)
            self.finish_round()

    def get_task_schedule(self, task_id, robot_id):
        """ Returns a dict
            start_time:  earliest start time according to the dispatchable graph
            finish_time: latest start time according to the dispatchable graph
        """
        timetable = self.timetable_manager.get(robot_id)

        r_earliest_start_time = timetable.dispatchable_graph.get_time(task_id, "start")
        r_earliest_pickup_time = timetable.dispatchable_graph.get_time(task_id, "pickup")
        r_latest_delivery_time = timetable.dispatchable_graph.get_time(task_id, "delivery", False)

        start_time = to_timestamp(self.timetable_manager.ztp, r_earliest_start_time)
        pickup_time = to_timestamp(self.timetable_manager.ztp, r_earliest_pickup_time)
        delivery_time = to_timestamp(self.timetable_manager.ztp, r_latest_delivery_time)

        self.logger.debug("Task %s start time: %s", task_id, start_time)
        self.logger.debug("Task %s pickup time : %s", task_id, pickup_time)
        self.logger.debug("Task %s latest delivery time: %s", task_id, delivery_time)

        task_schedule = {"start_time": start_time.to_datetime(),
                         "finish_time": delivery_time.to_datetime()}

        return task_schedule

