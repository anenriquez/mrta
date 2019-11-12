class InconsistentSchedule(Exception):

    def __init__(self, allotted_time):
        """ Raised when assigning a given time to a timepoint in an stn makes the
        temporal network inconsistent, i.e., attempting to schedule a task causes
        inconsistencies with the temporal constraints

        allotted_time (float): time (relative to the zero timepoint) assigned to the stn
        """
        Exception.__init__(self, allotted_time)
        self.relative_time = allotted_time


