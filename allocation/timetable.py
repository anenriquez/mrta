from allocation.exceptions.no_solution import NoSolution


class Timetable(object):
    """
    Each robot has a timetable, which contains temporal information about the robot's
    allocation:
    - stn:  Simple Temporal Network.
            Contains the allocated tasks along with the original temporal constraints

    - dispatchable graph:   Uses the same data structure as the stn and contains the same tasks, but
                            shrinks the original temporal constraints to the times at which the robot
                            can allocate the task
    """
    def __init__(self, stp, robot_id):
        self.stp = stp  # Simple Temporal Problem
        self.robot_id = robot_id
        self.stn = stp.get_stn()
        self.dispatchable_graph = stp.get_stn()
        self.robustness_metric = None

    def solve_stp(self):
        """ Computes the dispatchable graph and robustness metric from the
         given stn
        """
        result_stp = self.stp.compute_dispatchable_graph(self.stn)

        if result_stp is None:
            raise NoSolution()

        self.robustness_metric, self.dispatchable_graph = result_stp

    def add_task_to_stn(self, task, position):
        """
        Adds tasks to the stn at the given position
        :param task: task (obj) to add
        :param position: position where the task will be added
        """
        self.stn.add_task(task, position)

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



