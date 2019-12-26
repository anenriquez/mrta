from mrs.utils.as_dict import AsDictMixin


class RobotPose(AsDictMixin):
    def __init__(self, robot_id, pose):
        self.robot_id = robot_id
        self.pose = pose

    @property
    def meta_model(self):
        return "robot-pose"
