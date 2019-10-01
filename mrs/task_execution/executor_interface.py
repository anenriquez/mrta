import logging


class ExecutorInterface:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.logger = logging.getLogger("mrs.executor.interface")
        self.logger.debug("Executor interface initialized %s", self.robot_id)

