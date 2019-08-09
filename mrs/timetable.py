from mrs.exceptions.task_allocation import NoSTPSolution


class Timetable(object):
    """
    Each robot has a timetable, which contains temporal information about the robot's
    mrs:
    - stn:  Simple Temporal Network.
            Contains the allocated tasks along with the original temporal constraints

    - dispatchable graph:   Uses the same data structure as the stn and contains the same tasks, but
                            shrinks the original temporal constraints to the times at which the robot
                            can allocate the task

    - schedule: Uses the same data structure as the stn but contains only one task
                (the next task to be executed)
                The start navigation time is instantiated to a float value (seconds after epoch)
    """
    def __init__(self, stp, robot_id):
        self.stp = stp  # Simple Temporal Problem
        self.robustness_metric = None

        self.robot_id = robot_id
        self.stn = stp.get_stn()
        self.dispatchable_graph = stp.get_stn()
        self.schedule = stp.get_stn()

    def solve_stp(self):
        """ Computes the dispatchable graph and robustness metric from the
         given stn
        """
        result_stp = self.stp.compute_dispatchable_graph(self.stn)

        if result_stp is None:
            raise NoSTPSolution()

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

    def get_earliest_task_id(self):
        """ Returns the id of task with the earliest start time in the timetable

        :return: task_id (string)
        """
        task_id = self.stn.get_earliest_task_id()
        return task_id

    def to_dict(self):
        timetable_dict = dict()
        timetable_dict['robot_id'] = self.robot_id
        timetable_dict['stn'] = self.stn.to_json()
        timetable_dict['dispatchable_graph'] = self.dispatchable_graph.to_json()
        timetable_dict['schedule'] = self.schedule.to_json()

        return timetable_dict

    @staticmethod
    def from_dict(timetable_dict, stp):
        robot_id = timetable_dict['robot_id']
        timetable = Timetable(stp, robot_id)
        stn_cls = stp.get_stn()

        timetable.stn = stn_cls.from_json(timetable_dict['stn'])
        timetable.dispatchable_graph = stn_cls.from_json(timetable_dict['dispatchable_graph'])
        timetable.schedule = stn_cls.from_json(timetable_dict['schedule'])

        return timetable




