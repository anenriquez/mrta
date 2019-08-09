

class Scheduler(object):

    def __init__(self, robot_id, ccu_store, stp):
        self.id = robot_id
        self.ccu_store = ccu_store
        self.stp = stp

    def schedule(self, task):
        pass
