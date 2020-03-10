import logging.config
from fmlib.models.robot import Robot


class FleetMonitor:
    def __init__(self, api, **kwargs):
        self.api = api
        self.logger = logging.getLogger('mrs.fleet.monitor')
        self.robots = dict()

    def register_robot(self, robot_id):
        self.logger.debug("Registering robot %s", robot_id)
        robot = Robot.create_new(robot_id)
        self.robots[robot_id] = robot

    def robot_pose_cb(self, msg):
        payload = msg.get("payload")
        self.logger.debug("Received robot pose %s", payload)
        robot_id = payload.get("robotId")
        pose = payload.get("pose")
        self.update_robot_pose(robot_id, **pose)

    def get_robot_pose(self, robot_id):
        robot = self.robots.get(robot_id)
        return robot.position

    def update_robot_pose(self, robot_id, x, y, theta):
        self.logger.debug("Updating pose of robot %s", robot_id)
        robot = self.robots.get(robot_id)
        robot.update_position(x=x, y=y, theta=theta)
