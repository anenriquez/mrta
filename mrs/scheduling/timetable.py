import copy
import logging
from datetime import timedelta, datetime

from pymodm.errors import DoesNotExist
from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution
from stn.methods.fpc import get_minimal_network
from stn.task import InterTimepointConstraint as STNInterTimepointConstraint
from stn.task import Task as STNTask
from stn.task import TimepointConstraint as STNTimepointConstraint

from mrs.db.models.task import Task
from mrs.db.models.task import TimepointConstraint
from mrs.db.models.timetable import Timetable as TimetableMongo
from mrs.exceptions.allocation import TaskNotFound
from mrs.exceptions.execution import InconsistentAssignment

logger = logging.getLogger("mrs.timetable")


class Timetable(object):
    """
    Each robot has a timetable, which contains temporal information about the robot's
    allocated tasks:
    - stn (stn):    Simple Temporal Network.
                    Contains the allocated tasks along with the original temporal constraints

    - dispatchable graph (stn): Uses the same data structure as the stn and contains the same tasks, but
                            shrinks the original temporal constraints to the times at which the robot
                            can allocate the task

    """

    def __init__(self, robot_id, stp):
        self.robot_id = robot_id
        self.stp = stp  # Simple Temporal Problem
        self.zero_timepoint = self.initialize_zero_timepoint()

        self.stn = self.stp.get_stn()
        self.dispatchable_graph = self.stp.get_stn()

    @staticmethod
    def initialize_zero_timepoint():
        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        zero_timepoint = TimeStamp()
        zero_timepoint.timestamp = today_midnight
        return zero_timepoint

    def update_zero_timepoint(self, time_):
        self.zero_timepoint.timestamp = time_
        logger.debug("Zero timepoint updated to: %s", self.zero_timepoint)

    def compute_dispatchable_graph(self, stn):
        try:
            dispatchable_graph = self.stp.solve(stn)
            return dispatchable_graph
        except NoSTPSolution:
            raise NoSTPSolution()

    def solve_stp(self, task, insertion_point):
        stn_task = self.to_stn_task(task, insertion_point)
        stn = copy.deepcopy(self.stn)
        stn.add_task(stn_task, insertion_point)
        try:
            dispatchable_graph = self.stp.solve(stn)
            return stn, dispatchable_graph

        except NoSTPSolution:
            raise NoSTPSolution()

    def assign_timepoint(self, assigned_time, task_id, node_type):
        stn = copy.deepcopy(self.stn)
        minimal_network = get_minimal_network(stn)
        if minimal_network:
            minimal_network.assign_timepoint(assigned_time, task_id, node_type)
            if self.stp.is_consistent(minimal_network):
                self.stn.assign_timepoint(assigned_time, task_id, node_type)
                return
        raise InconsistentAssignment(assigned_time, task_id, node_type)

    def to_stn_task(self, task, insertion_point):
        self.update_pickup_constraint(task, insertion_point)
        self.update_start_constraint(task, insertion_point)
        self.update_delivery_constraint(task)
        stn_timepoint_constraints, stn_inter_timepoint_constraints = self.get_constraints(task)
        stn_task = STNTask(task.task_id, stn_timepoint_constraints, stn_inter_timepoint_constraints)
        return stn_task

    def update_pickup_constraint(self, task, insertion_point):
        hard_pickup_constraint = task.get_timepoint_constraint("pickup")
        pickup_time_window = hard_pickup_constraint.latest_time - hard_pickup_constraint.earliest_time

        if not task.constraints.hard:
            if insertion_point == 1:
                earliest_pickup_time = datetime.now() + timedelta(minutes=1)
                latest_pickup_time = earliest_pickup_time + pickup_time_window
                soft_pickup_constraint = TimepointConstraint(name="pickup",
                                                             earliest_time=earliest_pickup_time,
                                                             latest_time=latest_pickup_time)
            elif insertion_point > 1:
                r_earliest_delivery_time_previous_task = self.get_r_time_previous_task(insertion_point, "delivery")
                travel_time = task.get_inter_timepoint_constraint("travel_time")
                earliest_pickup_time = r_earliest_delivery_time_previous_task + (travel_time.mean - 2*travel_time.variance**0.5)

                latest_pickup_time = earliest_pickup_time + pickup_time_window.total_seconds()
                soft_pickup_constraint = TimepointConstraint(name="pickup",
                                                             earliest_time=TimepointConstraint.absolute_time(self.zero_timepoint, earliest_pickup_time),
                                                             latest_time=TimepointConstraint.absolute_time(self.zero_timepoint, latest_pickup_time))
            task.update_timepoint_constraint(**soft_pickup_constraint.to_dict())

    def previous_task_is_frozen(self, insertion_point):
        previous_task = self.get_task(insertion_point-1)
        if previous_task.frozen:
            return True
        return False

    def get_r_time_previous_task(self, insertion_point, node_type, earliest=True):
        # From stn or from dispatchable graph?
        previous_task = self.get_task(insertion_point-1)
        return self.dispatchable_graph.get_time(previous_task.task_id, node_type, earliest)

    def update_start_constraint(self, task, insertion_point):
        pickup_constraint = task.get_timepoint_constraint("pickup")
        travel_time = task.get_inter_timepoint_constraint("travel_time")
        stn_start_constraint = self.stn.get_prev_timepoint_constraint("start",
                                                                      STNTimepointConstraint(**pickup_constraint.to_dict_relative_to_ztp(self.zero_timepoint)),
                                                                      STNInterTimepointConstraint(**travel_time.to_dict()))

        if insertion_point > 1 and self.previous_task_is_frozen(insertion_point):
            r_latest_delivery_time_previous_task = self.get_r_time_previous_task(insertion_point, "delivery", earliest=False)
            stn_start_constraint.r_earliest_time = max(stn_start_constraint.r_earliest_time,
                                                       r_latest_delivery_time_previous_task)

        earliest_time = TimepointConstraint.absolute_time(self.zero_timepoint, stn_start_constraint.r_earliest_time)
        latest_time = TimepointConstraint.absolute_time(self.zero_timepoint, stn_start_constraint.r_latest_time)
        start_constraint = TimepointConstraint(name="start",
                                               earliest_time=earliest_time,
                                               latest_time=latest_time)

        task.update_timepoint_constraint(**start_constraint.to_dict())

    def update_delivery_constraint(self, task):
        pickup_constraint = task.get_timepoint_constraint("pickup")
        work_time = task.get_inter_timepoint_constraint("work_time")
        stn_delivery_constraint = self.stn.get_next_timepoint_constraint("delivery",
                                                                         STNTimepointConstraint(**pickup_constraint.to_dict_relative_to_ztp(self.zero_timepoint)),
                                                                         STNInterTimepointConstraint(**work_time.to_dict()))
        earliest_time = TimepointConstraint.absolute_time(self.zero_timepoint, stn_delivery_constraint.r_earliest_time)
        latest_time = TimepointConstraint.absolute_time(self.zero_timepoint, stn_delivery_constraint.r_latest_time)
        delivery_constraint = TimepointConstraint(name="delivery",
                                                  earliest_time=earliest_time,
                                                  latest_time=latest_time)
        task.update_timepoint_constraint(**delivery_constraint.to_dict())

    def get_constraints(self, task):
        stn_timepoint_constraints = list()
        stn_inter_timepoint_constraints = list()

        timepoint_constraints = task.get_timepoint_constraints()
        for constraint in timepoint_constraints:
            stn_timepoint_constraints.append(STNTimepointConstraint(**constraint.to_dict_relative_to_ztp(self.zero_timepoint)))

        inter_timepoint_constraints = task.get_inter_timepoint_constraints()
        for constraint in inter_timepoint_constraints:
            stn_inter_timepoint_constraints.append(STNInterTimepointConstraint(**constraint.to_dict()))

        return stn_timepoint_constraints, stn_inter_timepoint_constraints

    def get_tasks(self):
        """ Returns the tasks contained in the timetable

        :return: list of tasks
        """
        return self.stn.get_tasks()

    def get_task(self, position):
        """ Returns the task in the given position

        :param position: (int) position in the STN
        :return: (Task) task
        """
        task_id = self.stn.get_task_id(position)
        if task_id:
            return Task.get_task(task_id)
        else:
            raise TaskNotFound(position)

    def get_task_node_ids(self, task_id):
        return self.stn.get_task_node_ids(task_id)

    def get_next_task(self, task):
        task_last_node = self.stn.get_task_node_ids(task.task_id)[-1]
        if self.stn.has_node(task_last_node + 1):
            next_task_id = self.stn.nodes[task_last_node + 1]['data'].task_id
            try:
                next_task = Task.get_task(next_task_id)
            except DoesNotExist:
                logging.warning("Task %s is not in db", next_task_id)
                next_task = Task.create_new(task_id=next_task_id)
            return next_task

    def get_task_position(self, task_id):
        return self.stn.get_task_position(task_id)

    def task_exists(self, task_id):
        task_nodes = self.stn.get_task_node_ids(task_id)
        if task_nodes:
            return True
        return False

    def get_earliest_tasks(self, n_tasks=1):
        """ Returns a list of the earliest n_tasks in the timetable

        :return: list of tasks
        """
        tasks = list()
        for position in range(1, n_tasks+1):
            task_id = self.stn.get_task_id(position)
            if task_id:
                try:
                    tasks.append(Task.get_task(task_id))
                except DoesNotExist:
                    logging.warning("Task %s is not in db", task_id)
        return tasks

    def get_r_time(self, task_id, node_type='start', lower_bound=True):
        r_time = self.dispatchable_graph.get_time(task_id, node_type, lower_bound)
        return r_time

    def get_start_time(self, task_id):
        r_start_time = self.get_r_time(task_id)
        start_time = self.zero_timepoint + timedelta(seconds=r_start_time)
        return start_time

    def get_pickup_time(self, task_id):
        r_pickup_time = self.get_r_time(task_id, 'pickup', False)
        pickup_time = self.zero_timepoint + timedelta(seconds=r_pickup_time)
        return pickup_time

    def get_delivery_time(self, task_id):
        r_delivery_time = self.get_r_time(task_id, 'delivery', False)
        delivery_time = self.zero_timepoint + timedelta(seconds=r_delivery_time)
        return delivery_time

    def remove_task(self, task_id):
        task_node_ids = self.get_task_node_ids(task_id)
        if len(task_node_ids) < 3:
            self.stn.remove_node_ids(task_node_ids)
            self.dispatchable_graph.remove_node_ids(task_node_ids)
        else:
            node_id = self.get_task_position(task_id)
            self.stn.remove_task(node_id)
            self.dispatchable_graph.remove_task(node_id)
        self.store()

    def remove_node_ids(self, task_node_ids):
        self.stn.remove_node_ids(task_node_ids)
        self.dispatchable_graph.remove_node_ids(task_node_ids)
        self.store()

    def to_dict(self):
        timetable_dict = dict()
        timetable_dict['robot_id'] = self.robot_id
        timetable_dict['zero_timepoint'] = self.zero_timepoint.to_str()
        timetable_dict['stn'] = self.stn.to_dict()
        timetable_dict['dispatchable_graph'] = self.dispatchable_graph.to_dict()

        return timetable_dict

    @staticmethod
    def from_dict(timetable_dict, stp):
        robot_id = timetable_dict['robot_id']
        timetable = Timetable(robot_id, stp)
        stn_cls = timetable.stp.get_stn()

        zero_timepoint = timetable_dict.get('zero_timepoint')
        timetable.zero_timepoint = TimeStamp.from_str(zero_timepoint)
        timetable.stn = stn_cls.from_dict(timetable_dict['stn'])
        timetable.dispatchable_graph = stn_cls.from_dict(timetable_dict['dispatchable_graph'])

        return timetable

    def store(self):

        timetable = TimetableMongo(self.robot_id,
                                   self.zero_timepoint.to_datetime(),
                                   self.stn.to_dict(),
                                   self.dispatchable_graph.to_dict())
        timetable.save()

    def fetch(self):
        try:
            timetable_mongo = TimetableMongo.objects.get_timetable(self.robot_id)
            self.stn = self.stn.from_dict(timetable_mongo.stn)
            self.dispatchable_graph = self.stn.from_dict(timetable_mongo.dispatchable_graph)
            self.zero_timepoint = TimeStamp.from_datetime(timetable_mongo.zero_timepoint)
        except DoesNotExist:
            logging.debug("The timetable of robot %s is empty", self.robot_id)
            # Resetting values
            self.stn = self.stp.get_stn()
            self.dispatchable_graph = self.stp.get_stn()