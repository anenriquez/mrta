class AlternativeTimeSlot(Exception):

    def __init__(self, task_id, robot_id, alternative_start_time):
        """
        Raised when a task could not be allocated at the desired time slot.

        :param task_id:
        :param robot_id:
        :param alternative_start_time: earliest start time at which the task can start
                                    (lower bound of the dispatchable graph)
        """
        Exception.__init__(self, task_id, robot_id, alternative_start_time)
        self.task_id = task_id
        self.robot_id = robot_id
        self.alternative_start_time = alternative_start_time


class NoAllocation(Exception):

    def __init__(self, round_id):
        """ Raised when no mrs was possible

        """
        Exception.__init__(self, round_id)
        self.round_id = round_id


class NoSTPSolution(Exception):

    def __init__(self):
        """ Raised when the stp solver cannot produce a solution for the problem
        """
        Exception.__init__(self)
