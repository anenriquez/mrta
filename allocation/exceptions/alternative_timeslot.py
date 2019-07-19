class AlternativeTimeSlot(Exception):

    def __init__(self, task_id, robot_id, proposed_start_time):
        """
        Raised when a task could not be allocated at the desired time slot.

        :param task_id:
        :param robot_id:
        :param proposed_start_time: earliest start time at which the task can start
                                    (lower bound of the dispatchable graph)
        """
        Exception.__init__(self, task_id, robot_id, proposed_start_time)
