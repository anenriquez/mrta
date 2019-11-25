import logging
from datetime import timedelta

from fmlib.models.tasks import Task
from mrs.messages.task_announcement import TaskAnnouncement
from mrs.messages.task_contract import TaskContract
from mrs.allocation.round import Round
from mrs.db.models.task import TaskLot
from mrs.exceptions.allocation import AlternativeTimeSlot
from mrs.exceptions.allocation import InvalidAllocation
from mrs.exceptions.allocation import NoAllocation
from ropod.structs.task import TaskStatus as TaskStatusConst
from ropod.utils.timestamp import TimeStamp

""" Implements a variation of the the TeSSI algorithm using the bidding_rule 
specified in the config file
"""


class Auctioneer(object):

    def __init__(self, stp_solver, timetable_manager, round_time=5, freeze_window=300, **kwargs):

        self.logger = logging.getLogger("mrs.auctioneer")
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')
        self.robot_ids = list()
        self.timetable_manager = timetable_manager

        self.stp_solver = stp_solver

        self.round_time = timedelta(seconds=round_time)
        self.freeze_window = timedelta(seconds=freeze_window)
        self.alternative_timeslots = kwargs.get('alternative_timeslots', False)

        self.logger.debug("Auctioneer started")

        self.tasks_to_allocate = dict()
        self.allocations = list()
        self.waiting_for_user_confirmation = list()
        self.round = Round(self.timetable_manager.get_n_allocated_tasks())

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

    def update_tasks_to_allocate(self):
        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        for task in tasks:
            task_lot = TaskLot.get_task(task.task_id)
            self.tasks_to_allocate[task_lot.task.task_id] = task_lot

    def run(self):
        if self.tasks_to_allocate and self.round.finished:
            self.announce_task()

        if self.round.opened and self.round.time_to_close():
            try:
                if self.round.n_allocated_tasks == self.timetable_manager.get_n_allocated_tasks():
                    round_result = self.round.get_result()
                    self.process_round_result(round_result)
                else:
                    self.logger.warning("Round has to be repeated")
                    self.round.finish()

            except NoAllocation as exception:
                self.logger.warning("No allocation made in round %s ", exception.round_id)
                self.update_tasks_to_allocate()
                self.round.finish()

            except AlternativeTimeSlot as exception:
                self.process_alternative_timeslot(exception)

    def process_round_result(self, round_result):
        bid, time_to_allocate = round_result
        allocation = (bid.task_id, [bid.robot_id])
        self.process_allocation(allocation, time_to_allocate, bid)

    def process_alternative_timeslot(self, exception):
        bid = exception.bid
        time_to_allocate = exception.time_to_allocate
        alternative_start_time = bid.alternative_start_time
        alternative_allocation = (bid.task_id, [bid.robot_id], alternative_start_time)
        allocation = (bid.task_id, [bid.robot_id])

        self.logger.debug("Alternative timeslot for task %s: robot %s, alternative start time: %s ", bid.task_id,
                          bid.robot_id, bid.alternative_start_time)

        self.waiting_for_user_confirmation.append(alternative_allocation)

        # TODO: Prompt the user to accept the alternative timeslot
        # For now, accept always
        self.process_allocation(allocation, time_to_allocate, bid)

    def process_allocation(self, allocation, time_to_allocate,  bid):
        task_lot = self.tasks_to_allocate.pop(bid.task_id)
        try:
            self.timetable_manager.update_timetable(bid.robot_id, bid.insertion_point, bid.temporal_metric, task_lot)
            self.allocations.append(allocation)

            self.logger.debug("Allocation: %s", allocation)
            self.logger.debug("Tasks to allocate %s", [task_id for task_id, task in self.tasks_to_allocate.items()])

            self.logger.debug("Updating task status to ALLOCATED")
            task_lot.task.update_status(TaskStatusConst.ALLOCATED)
            task_lot.task.update_status(TaskStatusConst.PLANNED)
            task = Task.get_task(bid.task_id)
            task.assign_robots([bid.robot_id])

            self.announce_winner(allocation)

        except InvalidAllocation as e:
            self.logger.warning("The allocation of task %s to robot %s is inconsistent. Aborting allocation."
                                "Task %s will be included in next allocation round", e.task_id, e.robot_id, e.task_id)
            self.tasks_to_allocate[task_lot.task.task_id] = task_lot
            self.round.finish()

    def allocate(self, tasks):
        tasks_to_allocate = dict()
        if isinstance(tasks, list):
            self.logger.debug('Auctioneer received a list of tasks')
            for task in tasks:
                task_lot = TaskLot.from_task(task)
                tasks_to_allocate[task_lot.task.task_id] = task_lot
        else:
            self.logger.debug('Auctioneer received one task')
            task_lot = TaskLot.from_task(tasks)
            tasks_to_allocate[task_lot.task.task_id] = task_lot
        self.tasks_to_allocate = tasks_to_allocate

    def announce_task(self):
        self.timetable_manager.fetch_timetables()

        self.round = Round(self.timetable_manager.get_n_allocated_tasks(),
                           round_time=self.round_time,
                           alternative_timeslots=self.alternative_timeslots)

        self.logger.debug("Starting round: %s", self.round.id)
        self.logger.debug("Number of tasks to allocate: %s", len(self.tasks_to_allocate))

        tasks_lots = list(self.tasks_to_allocate.values())

        task_announcement = TaskAnnouncement(tasks_lots, self.round.id, self.timetable_manager.zero_timepoint)
        msg = self.api.create_message(task_announcement)

        self.logger.debug("Auctioneer announces tasks %s", [task_id for task_id, task in self.tasks_to_allocate.items()])

        self.round.start()
        self.api.publish(msg, groups=['TASK-ALLOCATION'])

    def bid_cb(self, msg):
        payload = msg['payload']
        self.round.process_bid(payload)

    def finish_round_cb(self, msg):
        self.round.finish()

    def announce_winner(self, allocation):
        task_id, robot_ids = allocation
        for robot_id in robot_ids:
            task_contract = TaskContract(task_id, robot_id)
            msg = self.api.create_message(task_contract)
            self.api.publish(msg, groups=['TASK-ALLOCATION'])

    def archive_task(self, robot_id, task_id, node_id):
        self.logger.debug("Deleting task %s", task_id)
        timetable = self.timetable_manager.get_timetable(robot_id)
        timetable.remove_task(node_id)
        task = Task.get_task(task_id)
        task.update_status(TaskStatusConst.COMPLETED)
        self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
        self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

    def get_task_schedule(self, task_id, robot_id):
        # For now, returning the start navigation time from the dispatchable graph
        task_schedule = dict()

        timetable = self.timetable_manager.timetables.get(robot_id)

        relative_start_navigation_time = timetable.dispatchable_graph.get_time(task_id, "navigation")
        relative_start_time = timetable.dispatchable_graph.get_time(task_id, "start")
        relative_latest_finish_time = timetable.dispatchable_graph.get_time(task_id, "finish", False)

        self.logger.debug("Current time %s: ", TimeStamp())
        self.logger.debug("zero_timepoint %s: ", self.timetable_manager.zero_timepoint)
        self.logger.debug("Relative start navigation time: %s", relative_start_navigation_time)
        self.logger.debug("Relative start time: %s", relative_start_time)
        self.logger.debug("Relative latest finish time: %s", relative_latest_finish_time)

        start_navigation_time = self.timetable_manager.zero_timepoint + timedelta(minutes=relative_start_navigation_time)
        start_time = self.timetable_manager.zero_timepoint + timedelta(minutes=relative_start_time)
        finish_time = self.timetable_manager.zero_timepoint + timedelta(minutes=relative_latest_finish_time)

        self.logger.debug("Start navigation of task %s: %s", task_id, start_navigation_time)
        self.logger.debug("Start of task %s: %s", task_id, start_time)
        self.logger.debug("Latest finish of task %s: %s", task_id, finish_time)

        task_schedule['start_time'] = start_navigation_time.to_datetime()
        task_schedule['finish_time'] = finish_time.to_datetime()

        return task_schedule

