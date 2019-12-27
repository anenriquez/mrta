class AlternativeTimeSlot(Exception):

    def __init__(self, bid, time_to_allocate):
        """
        Raised when a task could not be allocated at the desired time slot.

        bid (obj): winning bid for the alternative timeslot
        time_to_allocate (float)
        """
        Exception.__init__(self, bid, time_to_allocate)
        self.bid = bid
        self.time_to_allocate = time_to_allocate


class NoAllocation(Exception):

    def __init__(self, round_id):
        """ Raised when no allocation was possible in round_id

        """
        Exception.__init__(self, round_id)
        self.round_id = round_id


class NoSTPSolution(Exception):

    def __init__(self):
        """ Raised when the stp solver cannot produce a solution for the problem
        """
        Exception.__init__(self)


class InvalidAllocation(Exception):

    def __init__(self, task_id, robot_id, position):
        """ Raised when a winning bid produces an invalid allocation

        """
        self.task_id = task_id
        self.robot_id = robot_id
        self.position = position


class TaskNotFound(Exception):
    def __init__(self, position):
        """ Raised when attempting to read a task in a timetable position that does not exist"""
        self.position = position