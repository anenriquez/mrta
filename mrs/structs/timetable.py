from datetime import timedelta

import numpy as np
from ropod.structs.task import TaskConstraints
from ropod.utils.timestamp import TimeStamp
from stn.task import STNTask

from mrs.exceptions.task_allocation import NoSTPSolution


class Timetable(object):
    """
    Each robot has a timetable, which contains temporal information about the robot's
    allocated tasks:
    - stn:  Simple Temporal Network.
            Contains the allocated tasks along with the original temporal constraints

    - dispatchable graph:   Uses the same data structure as the stn and contains the same tasks, but
                            shrinks the original temporal constraints to the times at which the robot
                            can allocate the task

    - schedule: Uses the same data structure as the stn but contains only one task
                (the next task to be executed)
                The start navigation time is instantiated to a float value (seconds after epoch)
    """

    def __init__(self, stp, robot_id):
        self.stp = stp  # Simple Temporal Problem
        self.ztp = None
        self.risk_metric = np.inf
        self.temporal_metric = np.inf

        self.robot_id = robot_id
        self.stn = stp.get_stn()
        self.dispatchable_graph = stp.get_stn()
        self.schedule = stp.get_stn()

    def solve_stp(self):
        """ Computes the dispatchable graph, risk metric and temporal metric
        from the given stn
        """
        result_stp = self.stp.compute_dispatchable_graph(self.stn)

        if result_stp is None:
            raise NoSTPSolution()

        self.risk_metric, self.dispatchable_graph = result_stp

    def compute_temporal_metric(self, temporal_criterion):
        self.temporal_metric = self.stp.compute_temporal_metric(self.dispatchable_graph, temporal_criterion)

    def add_task_to_stn(self, task, ztp, position):
        """
        Adds tasks to the stn at the given position
        :param task: task (obj) to add
        :param position: position where the task will be added
        """
        stn_task = self.to_stn_task(task, ztp)
        self.ztp = ztp
        self.stn.add_task(stn_task, position)

    @staticmethod
    def to_stn_task(task, ztp):
        """ Converts a task to an stn task

        Args:
            task (obj): task to be converted
            ztp (TimeStamp): Zero Time Point. Origin time to which task temporal information is referenced to
        """

        r_earliest_start_time, r_latest_start_time = TaskConstraints.relative_to_ztp(task, ztp, "minutes")
        delta = timedelta(minutes=1)
        earliest_navigation_start = TimeStamp(delta)

        r_earliest_navigation_start = earliest_navigation_start.get_difference(ztp, "minutes")

        stn_task = STNTask(task.id,
                           r_earliest_navigation_start,
                           r_earliest_start_time,
                           r_latest_start_time,
                           task.start_pose_name,
                           task.finish_pose_name)

        return stn_task

    def remove_task_from_stn(self, position):
        """ Removes task from the stn at the given position
        :param position: task at this position will be removed
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
        task_id = self.stn.get_task_id(position)

    def get_earliest_task_id(self):
        """ Returns the id of the task with the earliest start time in the timetable

        :return: task_id (string)
        """
        task_id = self.stn.get_earliest_task_id()
        return task_id

    def remove_task(self, position=1):
        self.stn.remove_task(position)
        self.dispatchable_graph.remove_task(position)
        # Reset schedule (there is only one task in the schedule)
        self.schedule = self.stp.get_stn()

    def get_scheduled_task_id(self):
        task_ids = self.schedule.get_tasks()
        print("Task ids: ", task_ids)
        if not task_ids:
            return None
        task_id = task_ids.pop()
        return task_id

    def is_scheduled(self):
        task_id = self.get_scheduled_task_id()
        if task_id:
            return True
        return False

    def get_schedule(self, task_id):
        """ Gets an schedule (stn) containing the nodes associated with the task_id

        :param task_id: (string) id of the task
        :return: schedule (stn)
        """
        node_ids = self.dispatchable_graph.get_task_node_ids(task_id)
        self.schedule = self.dispatchable_graph.get_subgraph(node_ids)

    def to_dict(self):
        timetable_dict = dict()
        timetable_dict['robot_id'] = self.robot_id

        if self.ztp:
            timetable_dict['ztp'] = self.ztp.to_str()
        else:
            timetable_dict['ztp'] = self.ztp

        timetable_dict['risk_metric'] = self.risk_metric
        timetable_dict['temporal_metric'] = self.temporal_metric
        timetable_dict['stn'] = self.stn.to_dict()
        timetable_dict['dispatchable_graph'] = self.dispatchable_graph.to_dict()
        timetable_dict['schedule'] = self.schedule.to_dict()

        return timetable_dict

    @staticmethod
    def from_dict(timetable_dict, stp):
        robot_id = timetable_dict['robot_id']
        timetable = Timetable(stp, robot_id)
        stn_cls = stp.get_stn()

        ztp = timetable_dict.get('ztp')
        if ztp:
            timetable.ztp = TimeStamp.from_str(ztp)
        else:
            timetable.ztp = ztp

        timetable.risk_metric = timetable_dict['risk_metric']
        timetable.temporal_metric = timetable_dict['temporal_metric']
        timetable.stn = stn_cls.from_dict(timetable_dict['stn'])
        timetable.dispatchable_graph = stn_cls.from_dict(timetable_dict['dispatchable_graph'])
        timetable.schedule = stn_cls.from_dict(timetable_dict['schedule'])

        return timetable

    @staticmethod
    def get_timetable(db_interface, robot_id, stp):
        timetable = db_interface.get_timetable(robot_id, stp)
        if timetable is None:
            timetable = Timetable(stp, robot_id)
        return timetable



