import logging
from datetime import timedelta

from fleet_management.db.models.task import TimepointConstraints
from ropod.utils.timestamp import TimeStamp
from stn.task import STNTask

from mrs.exceptions.task_allocation import NoSTPSolution

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
        self.stp = stp  # Simple Temporal Problem
        self.zero_timepoint = None
        self.temporal_metric = None
        self.risk_metric = None

        self.robot_id = robot_id
        self.stn = self.initialize_stn()
        self.dispatchable_graph = None
        self.schedule = None

    def initialize_stn(self):
        """ Initializes an stn of the type used by the stp solver
        """
        return self.stp.get_stn()

    def solve_stp(self):
        """ Computes the dispatchable graph, risk metric and temporal metric
        from the given stn
        """
        result_stp = self.stp.solve(self.stn)

        if result_stp is None:
            raise NoSTPSolution()

        self.risk_metric, self.dispatchable_graph = result_stp

    def compute_temporal_metric(self, temporal_criterion):
        if self.dispatchable_graph:
            self.temporal_metric = self.stp.compute_temporal_metric(self.dispatchable_graph, temporal_criterion)
        else:
            logger.error("The dispatchable graph is empty. Solve the stp first")

    def add_task_to_stn(self, task, position):
        """
        Adds a task to the stn at the given position
        Args:
            task (obj): task object to add to the stn
            position (int) : position in the STN where the task will be added
        """
        stn_task = self.to_stn_task(task)
        self.stn.add_task(stn_task, position)

    def to_stn_task(self, task):
        """ Converts a task to an stn task

        Args:
            task (obj): task object to be converted
            zero_timepoint (TimeStamp): Zero Time Point. Origin time to which task temporal information is referenced to
        """
        start_timepoint_constraints = task.constraints.time_point_constraints[0]

        r_earliest_start_time, r_latest_start_time = TimepointConstraints.relative_to_ztp(start_timepoint_constraints,
                                                                                          self.zero_timepoint)
        delta = timedelta(minutes=1)
        earliest_navigation_start = TimeStamp(delta)
        r_earliest_navigation_start = earliest_navigation_start.get_difference(self.zero_timepoint, "minutes")

        stn_task = STNTask(task.task_id,
                           r_earliest_navigation_start,
                           r_earliest_start_time,
                           r_latest_start_time,
                           task.start_location,
                           task.finish_location)

        return stn_task

    def remove_task_from_stn(self, position):
        """ Removes task from the stn at the given position
        Args:
            position (int): the task at this position in the STN will be removed
        """
        self.stn.remove_task(position)

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

        timetable_dict['risk_metric'] = self.risk_metric
        timetable_dict['temporal_metric'] = self.temporal_metric

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
        stn_cls = timetable.initialize_stn()

        zero_timepoint = timetable_dict.get('zero_timepoint')
        if zero_timepoint:
            timetable.zero_timepoint = TimeStamp.from_str(zero_timepoint)
        else:
            timetable.zero_timepoint = zero_timepoint

        timetable.risk_metric = timetable_dict['risk_metric']
        timetable.temporal_metric = timetable_dict['temporal_metric']

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

