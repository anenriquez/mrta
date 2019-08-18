from ropod.utils.uuid import generate_uuid


class TaskAnnouncement(object):
    def __init__(self, tasks=[], round_id=''):
        """
        Struct with a list of tasks
        :param tasks: list of tasks
        """
        self.tasks = tasks
        if not round_id:
            self.round_id = generate_uuid()
        else:
            self.round_id = round_id

    def to_dict(self):
        task_annoucement_dict = dict()
        task_annoucement_dict['tasks'] = dict()

        for task in self.tasks:
            task_annoucement_dict['tasks'][task.id] = task.to_dict()

        task_annoucement_dict['round_id'] = self.round_id

        return task_annoucement_dict


class Allocation(object):
    def __init__(self, task_id, robot_id):
        self.task_id = task_id
        self.robot_id = robot_id

    def to_dict(self):
        allocation_dict = dict()
        allocation_dict['task_id'] = self.task_id
        allocation_dict['robot_id'] = self.robot_id
        return allocation_dict


class FinishRound(object):
    def __init__(self, robot_id):
        self.robot_id = robot_id

    def to_dict(self):
        finish_round = dict()
        finish_round['robot_id'] = self.robot_id
        return finish_round
