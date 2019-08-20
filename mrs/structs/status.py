class TaskStatus(object):
    UNALLOCATED = 1
    ALLOCATED = 2
    SCHEDULED = 3  # Task is ready to be dispatched
    SHIPPED = 4  # The task was sent to the robot
    ONGOING = 5
    COMPLETED = 6
    ABORTED = 7  # Aborted by the system, not by the user
    FAILED = 8  # Execution failed
    CANCELED = 9  # Canceled before execution starts
    PREEMPTED = 10  # Canceled during execution

    def __init__(self, task_id=''):
        self.task_id = task_id
        self.status = self.UNALLOCATED
        self.delayed = False

    def to_dict(self):
        task_dict = dict()
        task_dict['task_id'] = self.task_id
        task_dict['status'] = self.status
        task_dict['delayed'] = self.delayed
        return task_dict

    @staticmethod
    def from_dict(status_dict):
        task_id = status_dict['task_id']
        status = TaskStatus(task_id)
        status.task_id = task_id
        status.status = status_dict['status']
        status.delayed = status_dict['delayed']
        return status

    @staticmethod
    def to_csv(status_dict):
        """ Prepares dict to be written to a csv
        :return: dict
        """
        # The dictionary is already flat and ready to be exported
        return status_dict
