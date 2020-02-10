class AlternativeTimeSlot(Exception):

    def __init__(self, bid, tasks_to_allocate):
        """
        Raised when a task could not be allocated at the desired time slot.

        bid (obj): winning bid for the alternative timeslot
        tasks_to_allocate (dict): Remaining tasks to allocate
        """
        Exception.__init__(self, bid, tasks_to_allocate)
        self.bid = bid
        self.tasks_to_allocate = tasks_to_allocate


class NoAllocation(Exception):

    def __init__(self, round_id, tasks_to_allocate):
        """ Raised when no allocation was possible in round_id

        """
        Exception.__init__(self, round_id, tasks_to_allocate)
        self.round_id = round_id
        self.tasks_to_allocate = tasks_to_allocate


class InvalidAllocation(Exception):

    def __init__(self, task_id, robot_id, insertion_point):
        """ Raised when a winning bid produces an invalid allocation

        """
        self.task_id = task_id
        self.robot_id = robot_id
        self.insertion_point = insertion_point


class TaskNotFound(Exception):
    def __init__(self, position):
        """ Raised when attempting to read a task in a timetable position that does not exist"""
        self.position = position