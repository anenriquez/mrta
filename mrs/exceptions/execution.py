class InconsistentSchedule(Exception):

    def __init__(self, earliest_time, latest_time):
        """ Trying to assign a time (between earliest_time and latest_time)
         to a timepoint in an stn makes the temporal network inconsistent.

        e.g., attempting to schedule a task causes
        inconsistencies with the temporal constraints

        earliest_time (float): time relative to the zero timepoint
        latest_time (float): time relative to the zero timepoint
        """
        Exception.__init__(self, earliest_time, latest_time)
        self.earliest_time = earliest_time
        self.latest_time = latest_time


class InconsistentAssignment(Exception):

    def __init__(self, assigned_time, dispatchable_graph):
        """ Trying to assign assigned_time to a timepoint in dispatchable graph makes the temporal
        network inconsistent

        assigned_time (float): time relative to the zero timepoint
        dispatchable_graph (stn): dispatchable graph with assigned_time assigned
        """
        Exception.__init__(self, assigned_time, dispatchable_graph)
        self.assigned_time = assigned_time
        self.dispatchable_graph = dispatchable_graph


class MissingDispatchableGraph(Exception):
    def __init__(self, robot_id):
        """
        Raised when a component does not have a dispatchable graph
        Args:
            robot_id (str):  id of the robot, e.g. ropod_001

        """
        Exception.__init__(self, robot_id)
        self.robot_id = robot_id


