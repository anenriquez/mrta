import copy
import logging
from datetime import timedelta

from fmlib.models.tasks import TransportationTask as Task, TimepointConstraint
from stn.stp import STP

from mrs.db.models.timetable import Timetable as TimetableMongo
from mrs.exceptions.allocation import InvalidAllocation
from mrs.exceptions.allocation import TaskNotFound
from mrs.exceptions.execution import InconsistentAssignment
from mrs.messages.d_graph_update import DGraphUpdate
from mrs.simulation.simulator import SimulatorInterface
from mrs.timetable.stn_interface import STNInterface
from pymodm.errors import DoesNotExist
from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution
from stn.methods.fpc import get_minimal_network
from stn.task import Task as STNTask

from mrs.utils.time import to_timestamp


class Timetable(STNInterface):
    """
    Each robot has a timetable, which contains temporal information about the robot's
    allocated tasks:
    - stn (stn):    Simple Temporal Network.
                    Contains the allocated tasks along with the original temporal constraints

    - dispatchable graph (stn): Uses the same data structure as the stn and contains the same tasks, but
                            shrinks the original temporal constraints to the times at which the robot
                            can allocate the task

    """

    def __init__(self, robot_id, stp_solver, **kwargs):

        self.robot_id = robot_id
        self.stp_solver = stp_solver

        simulator_interface = SimulatorInterface(kwargs.get("simulator"))

        self.ztp = simulator_interface.init_ztp()
        self.stn = self.stp_solver.get_stn()
        self.dispatchable_graph = self.stp_solver.get_stn()
        super().__init__(self.ztp, self.stn, self.dispatchable_graph)

        self.logger = logging.getLogger("mrs.timetable.%s" % self.robot_id)
        self.logger.debug("Timetable %s started", self.robot_id)

    def update_ztp(self, time_):
        self.ztp.timestamp = time_
        self.logger.debug("Zero timepoint updated to: %s", self.ztp)

    def compute_dispatchable_graph(self, stn):
        try:
            dispatchable_graph = self.stp_solver.solve(stn)
            return dispatchable_graph
        except NoSTPSolution:
            raise NoSTPSolution()

    def assign_timepoint(self, assigned_time, node_id):
        stn = copy.deepcopy(self.stn)
        minimal_network = get_minimal_network(stn)
        if minimal_network:
            minimal_network.assign_timepoint(assigned_time, node_id, force=True)
            if self.stp_solver.is_consistent(minimal_network):
                self.stn.assign_timepoint(assigned_time, node_id, force=True)
                return
        node = self.stn.get_node(node_id)
        raise InconsistentAssignment(assigned_time, node.task_id, node.node_type)

    def is_next_task_invalid(self, task, next_task):
        finish_current_task = self.dispatchable_graph.get_time(task.task_id, 'delivery', False)
        earliest_start_next_task = self.dispatchable_graph.get_time(next_task.task_id, 'start')
        latest_start_next_task = self.dispatchable_graph.get_time(next_task.task_id, 'start', False)
        if latest_start_next_task < finish_current_task:
            self.logger.warning("Task %s is invalid", next_task.task_id)
            return True
        elif earliest_start_next_task < finish_current_task:
            # Next task is valid but we need to update its earliest start time
            self.dispatchable_graph.assign_earliest_time(finish_current_task, next_task.task_id, "start", force=True)
        return False

    def update_timepoint(self, assigned_time, node_id):
        self.stn.assign_timepoint(assigned_time, node_id, force=True)
        self.stn.execute_timepoint(node_id)
        self.dispatchable_graph.assign_timepoint(assigned_time, node_id, force=True)
        self.dispatchable_graph.execute_timepoint(node_id)

    def execute_edge(self, start_node_id, finish_node_id):
        self.stn.execute_edge(start_node_id, finish_node_id)
        self.stn.remove_old_timepoints()
        self.dispatchable_graph.execute_edge(start_node_id, finish_node_id)
        self.dispatchable_graph.remove_old_timepoints()

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
            try:
                return Task.get_task(task_id)
            except DoesNotExist:
                self.logger.warning("Task %s is not in db", task_id)
                raise DoesNotExist
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
                self.logger.warning("Task %s is not in db", next_task_id)
                next_task = Task.create_new(task_id=next_task_id)
            return next_task

    def get_previous_task(self, task):
        task_first_node = self.stn.get_task_node_ids(task.task_id)[0]
        if task_first_node > 1 and self.stn.has_node(task_first_node - 1):
            prev_task_id = self.stn.nodes[task_first_node - 1]['data'].task_id
            prev_task = Task.get_task(prev_task_id)
            return prev_task

    def get_task_position(self, task_id):
        return self.stn.get_task_position(task_id)

    def has_task(self, task_id):
        task_nodes = self.stn.get_task_node_ids(task_id)
        if task_nodes:
            return True
        return False

    def get_earliest_task(self):
        task_id = self.stn.get_earliest_task_id()
        if task_id:
            try:
                task = Task.get_task(task_id)
                return task
            except DoesNotExist:
                self.logger.warning("Task %s is not in db or its first node is not the start node", task_id)

    def get_r_time(self, task_id, node_type, lower_bound):
        r_time = self.dispatchable_graph.get_time(task_id, node_type, lower_bound)
        return r_time

    def get_start_time(self, task_id, lower_bound=True):
        r_start_time = self.get_r_time(task_id, 'start', lower_bound)
        start_time = self.ztp + timedelta(seconds=r_start_time)
        return start_time

    def get_pickup_time(self, task_id, lower_bound=True):
        r_pickup_time = self.get_r_time(task_id, 'pickup', lower_bound)
        pickup_time = self.ztp + timedelta(seconds=r_pickup_time)
        return pickup_time

    def get_delivery_time(self, task_id, lower_bound=True):
        r_delivery_time = self.get_r_time(task_id, 'delivery', lower_bound)
        delivery_time = self.ztp + timedelta(seconds=r_delivery_time)
        return delivery_time

    def check_is_task_delayed(self, task, assigned_time, node_id):
        latest_time = self.dispatchable_graph.get_node_latest_time(node_id)
        if assigned_time > latest_time:
            self.logger.warning("Task %s is delayed", task.task_id)
            task.delayed = True

    def remove_task(self, task_id):
        self.remove_task_from_stn(task_id)
        self.remove_task_from_dispatchable_graph(task_id)
        if str(task_id) in self.stn_tasks:
            self.stn_tasks.pop(str(task_id))

    def remove_task_from_stn(self, task_id):
        task_node_ids = self.stn.get_task_node_ids(task_id)
        if 0 < len(task_node_ids) < 3:
            self.stn.remove_node_ids(task_node_ids)
        elif len(task_node_ids) == 3:
            node_id = self.stn.get_task_position(task_id)
            self.stn.remove_task(node_id)
        else:
            self.logger.warning("Task %s is not in timetable", task_id)
        self.store()

    def remove_task_from_dispatchable_graph(self, task_id):
        task_node_ids = self.dispatchable_graph.get_task_node_ids(task_id)
        if 0 < len(task_node_ids) < 3:
            self.dispatchable_graph.remove_node_ids(task_node_ids)
        elif len(task_node_ids) == 3:
            node_id = self.dispatchable_graph.get_task_position(task_id)
            self.dispatchable_graph.remove_task(node_id)
        else:
            self.logger.warning("Task %s is not in timetable", task_id)
        self.store()

    def remove_node_ids(self, task_node_ids):
        self.stn.remove_node_ids(task_node_ids)
        self.dispatchable_graph.remove_node_ids(task_node_ids)
        self.store()

    def get_timepoint_constraint(self, task_id, constraint_name):
        earliest_time = to_timestamp(self.ztp,
                                     self.get_r_time(task_id, constraint_name, lower_bound=True)).to_datetime()
        latest_time = to_timestamp(self.ztp,
                                   self.get_r_time(task_id, constraint_name, lower_bound=False)).to_datetime()
        constraint = TimepointConstraint(earliest_time, latest_time)
        return constraint

    def get_d_graph_update(self, n_tasks):
        sub_stn = self.stn.get_subgraph(n_tasks)
        sub_dispatchable_graph = self.dispatchable_graph.get_subgraph(n_tasks)
        return DGraphUpdate(self.ztp, sub_stn, sub_dispatchable_graph)

    def to_dict(self):
        timetable_dict = dict()
        timetable_dict['robot_id'] = self.robot_id
        timetable_dict['solver_name'] = self.stp_solver.solver_name
        timetable_dict['ztp'] = self.ztp.to_str()
        timetable_dict['stn'] = self.stn.to_dict()
        timetable_dict['dispatchable_graph'] = self.dispatchable_graph.to_dict()
        timetable_dict['stn_tasks'] = self.stn_tasks

        return timetable_dict

    @staticmethod
    def from_dict(timetable_dict):
        robot_id = timetable_dict['robot_id']
        stp_solver = STP(timetable_dict['solver_name'])
        timetable = Timetable(robot_id, stp_solver)
        stn_cls = timetable.stp_solver.get_stn()

        ztp = timetable_dict.get('ztp')
        timetable.ztp = TimeStamp.from_str(ztp)
        timetable.stn = stn_cls.from_dict(timetable_dict['stn'])
        timetable.dispatchable_graph = stn_cls.from_dict(timetable_dict['dispatchable_graph'])
        timetable.stn_tasks = timetable_dict['stn_tasks']

        return timetable

    def to_model(self):
        stn_tasks = {task_id: task.to_dict() for (task_id, task) in self.stn_tasks.items()}

        timetable_model = TimetableMongo(self.robot_id,
                                         self.stp_solver.solver_name,
                                         self.ztp.to_datetime(),
                                         self.stn.to_dict(),
                                         self.dispatchable_graph.to_dict(),
                                         stn_tasks)
        return timetable_model

    def store(self):
        timetable = self.to_model()
        timetable.save()

    def fetch(self):
        try:
            self.logger.debug("Fetching timetable of robot %s", self.robot_id)
            timetable_mongo = TimetableMongo.objects.get_timetable(self.robot_id)
            self.stn = self.stn.from_dict(timetable_mongo.stn)
            self.dispatchable_graph = self.stn.from_dict(timetable_mongo.dispatchable_graph)
            self.ztp = TimeStamp.from_datetime(timetable_mongo.ztp)
            self.stn_tasks = {task_id: STNTask.from_dict(task) for (task_id, task) in timetable_mongo.stn_tasks.items()}

        except DoesNotExist:
            self.logger.debug("The timetable of robot %s is empty", self.robot_id)
            # Resetting values
            self.stn = self.stp_solver.get_stn()
            self.dispatchable_graph = self.stp_solver.get_stn()


class TimetableManager(dict):
    """
    Manages the timetable of all the robots in the fleet
    """
    def __init__(self, stp_solver, **kwargs):
        super().__init__()
        self.logger = logging.getLogger("mrs.timetable.manager")
        self.stp_solver = stp_solver
        self.simulator = kwargs.get('simulator')

        self.logger.debug("TimetableManager started")

    @property
    def ztp(self):
        if self:
            any_timetable = next(iter(self.values()))
            return any_timetable.ztp
        else:
            self.logger.error("The zero timepoint has not been initialized")

    @ztp.setter
    def ztp(self, time_):
        for robot_id, timetable in self.items():
            timetable.update_zero_timepoint(time_)

    def get_timetable(self, robot_id):
        return self.get(robot_id)

    def register_robot(self, robot_id):
        self.logger.debug("Registering robot %s", robot_id)
        timetable = Timetable(robot_id, self.stp_solver, simulator=self.simulator)
        timetable.fetch()
        self[robot_id] = timetable
        timetable.store()

    def fetch_timetables(self):
        for robot_id, timetable in self.items():
            timetable.fetch()

    def update_timetable(self, robot_id, allocation_info, task):
        timetable = self.get(robot_id)
        stn = copy.deepcopy(timetable.stn)

        stn.add_task(allocation_info.new_task, allocation_info.insertion_point)
        if allocation_info.next_task:
            stn.update_task(allocation_info.next_task)

        try:
            timetable.dispatchable_graph = timetable.compute_dispatchable_graph(stn)

        except NoSTPSolution:
            self.logger.warning("The STN is inconsistent with task %s in insertion point %s", task.task_id,
                                allocation_info.insertion_point)
            self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

            raise InvalidAllocation(task.task_id, robot_id, allocation_info.insertion_point)

        timetable.add_stn_task(allocation_info.new_task)
        if allocation_info.next_task:
            timetable.add_stn_task(allocation_info.next_task)

        timetable.stn = stn
        self.update({robot_id: timetable})
        timetable.store()

        self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
        self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

