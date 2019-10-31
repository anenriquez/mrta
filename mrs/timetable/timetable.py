import logging
from datetime import timedelta, datetime

from fmlib.models.tasks import TimepointConstraints
from mrs.db.models.timetable import Timetable as TimetableMongo
from stn.exceptions.stp import NoSTPSolution
from pymodm.errors import DoesNotExist
from ropod.utils.timestamp import TimeStamp
from stn.task import STNTask
import copy

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
        self.zero_timepoint = None

        self.stn = self.stp.get_stn()
        self.dispatchable_graph = self.stp.get_stn()
        self.schedule = self.stp.get_stn()

    def solve_stp(self, task_lot, insertion_point):
        task = self.to_stn_task(task_lot, insertion_point)
        stn = copy.deepcopy(self.stn)
        stn.add_task(task, insertion_point)

        try:
            dispatchable_graph = self.stp.solve(stn)
            return stn, dispatchable_graph

        except NoSTPSolution:
            raise NoSTPSolution()

    def to_stn_task(self, task_lot, insertion_point):
        """ Converts a task to an stn task

        Args:
            task_lot (obj): task_lot object to be converted
            insertion_point(int): position in the stn in which the task will be insterted
        """
        if not task_lot.constraints.hard:
            # Get latest finish time of task in previous position
            if insertion_point > 1:
                previous_task_id = self.dispatchable_graph.get_task_id(insertion_point-1)
                r_latest_finish_time = self.dispatchable_graph.get_time(previous_task_id, "finish", False)

                latest_finish_time = self.zero_timepoint + timedelta(minutes=r_latest_finish_time)
                earliest_time = latest_finish_time + timedelta(minutes=5)
                latest_time = earliest_time + timedelta(minutes=5)

                start_timepoint_constraints = TimepointConstraints(earliest_time=earliest_time.to_datetime(),
                                                                   latest_time=latest_time.to_datetime())
            else:

                start_time = datetime.now() + timedelta(minutes=1)
                start_timepoint_constraints = TimepointConstraints(earliest_time=start_time,
                                                                   latest_time=start_time)
        else:
            start_timepoint_constraints = task_lot.constraints.timepoint_constraints[0]

        r_earliest_start_time, r_latest_start_time = TimepointConstraints.relative_to_ztp(start_timepoint_constraints,
                                                                                          self.zero_timepoint)
        r_earliest_navigation_start = r_earliest_start_time - 0.5

        stn_task = STNTask(task_lot.task.task_id,
                           r_earliest_navigation_start,
                           r_earliest_start_time,
                           r_latest_start_time,
                           task_lot.start_location,
                           task_lot.finish_location,
                           hard_constraints=task_lot.constraints.hard)

        return stn_task

    def get_tasks(self):
        """ Returns the tasks contained in the timetable

        :return: list of tasks
        """
        return self.stn.get_tasks()

    def get_task_id(self, position):
        """ Returns the id of the task in the given position

        :param position: (int) position in the STN
        :return: (string) task id
        """
        return self.stn.get_task_id(position)

    def get_earliest_task_id(self):
        """ Returns the id of the task with the earliest start time in the timetable

        :return: task_id (string)
        """
        return self.stn.get_earliest_task_id()

    def remove_task(self, position=1):
        self.stn.remove_task(position)
        self.dispatchable_graph.remove_task(position)
        # Reset schedule (there is only one task in the schedule)
        self.schedule = None

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

        if self.zero_timepoint:
            timetable_dict['zero_timepoint'] = self.zero_timepoint.to_str()
        else:
            timetable_dict['zero_timepoint'] = self.zero_timepoint

        if self.stn:
            timetable_dict['stn'] = self.stn.to_dict()
        else:
            timetable_dict['stn'] = self.stn

        if self.dispatchable_graph:
            timetable_dict['dispatchable_graph'] = self.dispatchable_graph.to_dict()
        else:
            timetable_dict['dispatchable_graph'] = self.dispatchable_graph

        if self.schedule:
            timetable_dict['schedule'] = self.schedule.to_dict()
        else:
            timetable_dict['schedule'] = self.schedule

        return timetable_dict

    @staticmethod
    def from_dict(timetable_dict, stp):
        robot_id = timetable_dict['robot_id']
        timetable = Timetable(robot_id, stp)
        stn_cls = timetable.stp.get_stn()

        zero_timepoint = timetable_dict.get('zero_timepoint')
        if zero_timepoint:
            timetable.zero_timepoint = TimeStamp.from_str(zero_timepoint)
        else:
            timetable.zero_timepoint = zero_timepoint

        stn = timetable_dict.get('stn')
        if stn:
            timetable.stn = stn_cls.from_dict(stn)
        else:
            timetable.stn = stn

        dispatchable_graph = timetable_dict.get('dispatchable_graph')
        if dispatchable_graph:
            timetable.dispatchable_graph = stn_cls.from_dict(dispatchable_graph)
        else:
            timetable.dispatchable_graph = dispatchable_graph

        schedule = timetable_dict.get('schedule')
        if schedule:
            timetable.schedule = stn_cls.from_dict(schedule)
        else:
            timetable.schedule = schedule

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
            self.zero_timepoint = timetable_mongo.zero_timepoint
            self.dispatchable_graph.temporal_metric = timetable_mongo.temporal_metric
            self.dispatchable_graph.risk_metric = timetable_mongo.risk_metric
        except DoesNotExist as err:
            logging.debug("The timetable of robot %s is empty", self.robot_id)
            self.stn = self.stp.get_stn()
            self.dispatchable_graph = None
            self.zero_timepoint = None
            self.schedule = None

