from mrs.task_execution.dispatching.scheduler import Scheduler
from mrs.timetable import Timetable
from stn.stp import STP


class Dispatcher(object):

    def __init__(self, robot_id, ccu_store, task_cls, stp_solver):
        self.id = robot_id
        self.ccu_store = ccu_store
        self.task_cls = task_cls
        self.stp = STP(stp_solver)

        self.scheduler = Scheduler(robot_id, ccu_store, self.stp)

    def get_timetable(self):
        timetable_dict = self.ccu_store.get_timetable(self.id)
        print("Timetable dict: ", timetable_dict)
        if timetable_dict is None:
            return
        timetable = Timetable.from_dict(timetable_dict, self.stp)
        return timetable

    def run(self):
        print("Running dispatcher")
        timetable = self.get_timetable()
        task_id = timetable.get_earliest_task_id()
        if task_id:
            print("------>", task_id)
            task_dict = self.ccu_store.get_task(task_id)
            task = self.task_cls.from_dict(task_dict)
            print("------>", task)

