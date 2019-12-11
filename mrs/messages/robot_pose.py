from fmlib.utils.messages import Document


class RobotPose:
    def __init__(self, robot_id, pose):
        self.robot_id = robot_id
        self.pose = pose

    def to_dict(self):
        dict_repr = dict()
        dict_repr['robot_id'] = self.robot_id
        dict_repr['pose'] = self.pose

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        robot_pose = cls(**document)
        return robot_pose

    @property
    def meta_model(self):
        return "robot-pose"
