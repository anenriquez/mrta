import copy
import logging
from datetime import timedelta, datetime

from fmlib.models.tasks import Task
from fmlib.models.tasks import TimepointConstraints
from pymodm.errors import DoesNotExist
from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution
from stn.task import STNTask

from mrs.db.models.task import TaskLot
from mrs.db.models.timetable import Timetable as TimetableMongo

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

    - schedule (stn): Uses the same data structure as the stn but contains only one task
                (the next task to be executed)
                The start navigation time is instantiated to a float value (minutes after zero_timepoint)
    """

    def __init__(self, robot_id, stp):
        self.robot_id = robot_id
        self.stp = stp  # Simple Temporal Problem
        self.zero_timepoint = self.initialize_zero_timepoint()

        self.stn = self.stp.get_stn()
        self.dispatchable_graph = self.stp.get_stn()
        self.schedule = self.stp.get_stn()

    @staticmethod
    def initialize_zero_timepoint():
        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        zero_timepoint = TimeStamp()
        zero_timepoint.timestamp = today_midnight
        return zero_timepoint

    def update_zero_timepoint(self):
        pass

    def solve_stp(self, task_lot, insertion_point):
        task = self.to_stn_task(task_lot, insertion_point)
        stn = copy.deepcopy(self.stn)
        stn.add_task(task, insertion_point)
        try:
            dispatchable_graph = self.stp.solve(stn)
            return stn, dispatchable_graph

        except NoSTPSolution:
            raise NoSTPSolution()

    def get_hard_constraints(self, task_lot, insertion_point):
        start_timepoint = task_lot.constraints.timepoint_constraints[0]

        if insertion_point == 1:
            # TODO: Get navigation constraints using duration travel info:
            #  [mu - 2sd, mu + 2sd] from current pose to start_pose of new task
            earliest_navigation_start = start_timepoint.earliest_time - timedelta(minutes=0.5)
            navigation_timepoint = \
                TimepointConstraints(earliest_time=earliest_navigation_start,
                                     latest_time=earliest_navigation_start)
        else:
            previous_task_id = self.dispatchable_graph.get_task_id(insertion_point-1)
            previous_task = TaskLot.get_task(previous_task_id)

            if previous_task.frozen:
                r_latest_finish_time = self.dispatchable_graph.get_time(previous_task_id, "finish", False)
                earliest_navigation_start = self.zero_timepoint + timedelta(minutes=r_latest_finish_time)
                navigation_timepoint = TimepointConstraints(earliest_time=earliest_navigation_start.to_datetime(),
                                                            latest_time=earliest_navigation_start.to_datetime())
            else:
                navigation_timepoint = TimepointConstraints(earliest_time=self.zero_timepoint.to_datetime(),
                                                            latest_time=self.zero_timepoint.to_datetime())

        return navigation_timepoint, start_timepoint

    def get_soft_constraints(self, task_lot, insertion_point):
        if insertion_point == 1:
            # Try to start task as soon as possible
            start_time = datetime.now() + timedelta(minutes=1)
            start_timepoint = TimepointConstraints(earliest_time=start_time)

            # TODO: Get start constraints using duration travel info:
            #  [mu - 2sd, mu + 2sd] from current pose to start_pose of new task
            earliest_navigation_start = start_timepoint.earliest_time - timedelta(minutes=0.5)
            navigation_timepoint = \
                TimepointConstraints(earliest_time=earliest_navigation_start,
                                     latest_time=earliest_navigation_start)
        else:
            previous_task_id = self.dispatchable_graph.get_task_id(insertion_point-1)
            previous_task = TaskLot.get_task(previous_task_id)
            r_latest_finish_time = self.dispatchable_graph.get_time(previous_task_id, "finish", False)

            latest_finish_time = self.zero_timepoint + timedelta(minutes=r_latest_finish_time)

            if previous_task.frozen:
                navigation_timepoint = TimepointConstraints(earliest_time=latest_finish_time.to_datetime(),
                                                            latest_time=latest_finish_time.to_datetime())
            else:
                navigation_timepoint = TimepointConstraints(earliest_time=self.zero_timepoint.to_datetime(),
                                                            latest_time=self.zero_timepoint.to_datetime())

            # TODO: Get start constraints using duration travel info:
            #  [mu - 2sd, mu + 2sd] from finish_pose of last task to start_pose of new task
            earliest_time = latest_finish_time + timedelta(minutes=5)
            latest_time = earliest_time + timedelta(minutes=6)
            start_timepoint = TimepointConstraints(earliest_time=earliest_time.to_datetime(),
                                                   latest_time=latest_time.to_datetime())

        return navigation_timepoint, start_timepoint

    def to_stn_task(self, task_lot, insertion_point):
        """ Converts a task to an stn task

        Args:
            task_lot (obj): task_lot object to be converted
            insertion_point(int): position in the stn in which the task will be insterted
        """
        if task_lot.constraints.hard:
            navigation_timepoint, start_timepoint = self.get_hard_constraints(task_lot, insertion_point)
        else:
            navigation_timepoint, start_timepoint = self.get_soft_constraints(task_lot, insertion_point)

        r_earliest_start_time, r_latest_start_time = TimepointConstraints.relative_to_ztp(start_timepoint,
                                                                                          self.zero_timepoint)
        r_earliest_navigation_time, r_latest_navigation_time = TimepointConstraints.relative_to_ztp(navigation_timepoint,
                                                                                                    self.zero_timepoint)
        stn_task = STNTask(task_lot.task.task_id,
                           r_earliest_navigation_time,
                           r_earliest_start_time,
                           r_latest_start_time,
                           task_lot.start_location,
                           task_lot.finish_location)
        return stn_task

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

    def get_earliest_tasks(self, n_tasks=2):
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

    def get_r_time(self, task_id, node_type='navigation', lower_bound=True):
        r_time = self.dispatchable_graph.get_time(task_id, node_type, lower_bound)
        return r_time

    def get_start_time(self, task_id):
        r_start_time = self.get_r_time(task_id)
        start_time = self.zero_timepoint + timedelta(minutes=r_start_time)
        return start_time

    def get_pickup_time(self, task_id):
        r_pickup_time = self.get_r_time(task_id, 'start', False)
        pickup_time = self.zero_timepoint + timedelta(minutes=r_pickup_time)
        return pickup_time

    def get_finish_time(self, task_id):
        r_finish_time = self.get_r_time(task_id, 'finish', False)
        finish_time = self.zero_timepoint + timedelta(minutes=r_finish_time)
        return finish_time

    def remove_task(self, position=1):
        self.stn.remove_task(position)
        self.dispatchable_graph.remove_task(position)
        self.store()

    def get_scheduled_task_id(self):
        if self.schedule is None:
            logger.error("No tasks scheduled")
            return

        task_ids = self.schedule.get_tasks()
        task_id = task_ids.pop()
        return task_id

    def get_schedule(self, task_id):
        """ Gets an schedule (stn) containing the nodes associated with the task_id

        :param task_id: (string) id of the task
        :return: schedule (stn)
        """
        if self.dispatchable_graph:
            node_ids = self.dispatchable_graph.get_task_node_ids(task_id)
            self.schedule = self.dispatchable_graph.get_subgraph(node_ids)
        else:
            logger.error("The dispatchable graph is empty")

    def to_dict(self):
        timetable_dict = dict()
        timetable_dict['robot_id'] = self.robot_id
        timetable_dict['zero_timepoint'] = self.zero_timepoint.to_str()
        timetable_dict['stn'] = self.stn.to_dict()
        timetable_dict['dispatchable_graph'] = self.dispatchable_graph.to_dict()
        timetable_dict['schedule'] = self.schedule.to_dict()

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
        timetable.schedule = stn_cls.from_dict(timetable_dict['schedule'])

        return timetable

    def store(self):

        timetable = TimetableMongo(self.robot_id,
                                   self.zero_timepoint.to_datetime(),
                                   self.dispatchable_graph.temporal_metric,
                                   self.dispatchable_graph.risk_metric,
                                   self.stn.to_dict(),
                                   self.dispatchable_graph.to_dict())
        timetable.save()

    def fetch(self):
        try:
            timetable_mongo = TimetableMongo.objects.get_timetable(self.robot_id)
            self.stn = self.stn.from_dict(timetable_mongo.stn)
            self.dispatchable_graph = self.stn.from_dict(timetable_mongo.dispatchable_graph)
            self.zero_timepoint = TimeStamp.from_datetime(timetable_mongo.zero_timepoint)
            self.dispatchable_graph.temporal_metric = timetable_mongo.temporal_metric
            self.dispatchable_graph.risk_metric = timetable_mongo.risk_metric
        except DoesNotExist:
            logging.debug("The timetable of robot %s is empty", self.robot_id)
            # Resetting values
            self.stn = self.stp.get_stn()
            self.dispatchable_graph = self.stp.get_stn()
            self.schedule = self.stp.get_stn()



