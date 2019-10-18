class InconsistentSchedule(Exception):

    def __init__(self, task):
        """ Raised if attempting to schedule task causes inconsistencies with the
        temporal constraints in the dispatchable graph

        :param task: (obj) task to be scheduled
        """
        Exception.__init__(self, task)
        self.task = task
