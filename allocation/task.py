from allocation.utils.uuid import generate_uuid


class Task(object):

    def __init__(self, id='', earliest_start_time=-1, latest_start_time=-1, pickup_pose_name='', delivery_pose_name=''):

        if not id:
            self.id = generate_uuid()
        else:
            self.id = id

        self.earliest_start_time = earliest_start_time
        self.latest_start_time = latest_start_time
        self.pickup_pose_name = pickup_pose_name
        self.delivery_pose_name = delivery_pose_name

    def to_dict(self):
        task_dict = dict()
        task_dict['id'] = self.id
        task_dict['earliest_start_time'] = self.earliest_start_time
        task_dict['latest_start_time'] = self.latest_start_time
        task_dict['pickup_pose_name'] = self.pickup_pose_name
        task_dict['delivery_pose_name'] = self.delivery_pose_name
        return task_dict

    @staticmethod
    def from_dict(task_dict):
        task = Task()
        task.id = task_dict['id']
        task.earliest_start_time = task_dict['earliest_start_time']
        task.latest_start_time = task_dict['latest_start_time']
        task.pickup_pose_name = task_dict['pickup_pose_name']
        task.delivery_pose_name = task_dict['delivery_pose_name']
        return task
