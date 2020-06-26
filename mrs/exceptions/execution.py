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

    def __init__(self, assigned_time, task_id, node_type):
        """ Trying to assign assigned_time to the node_type of task_id makes the temporal
        network inconsistent

        assigned_time (float): time relative to the zero timepoint
        task_id (UUID): id that uniquely identifies the task
        node_type(str): type of the node (start, pickup, delivery)
        """
        Exception.__init__(self, assigned_time, task_id, node_type)
        self.assigned_time = assigned_time
        self.task_id = task_id
        self.node_type = node_type


class EmptyTimetable(Exception):
    def __init__(self):
        """Raised when the timetable is empty"""
