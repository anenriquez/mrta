from ropod.utils.timestamp import TimeStamp as ts
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

        self.timetable = self.get_timetable()

    def get_timetable(self):
        timetable_dict = self.ccu_store.get_timetable(self.id)
        if timetable_dict is None:
            return
        self.timetable = Timetable.from_dict(timetable_dict, self.stp)
        return self.timetable

    def run(self):

        if not self.scheduler.task_scheduled and self.get_timetable():
            task = self.get_next_task_to_schedule()
            if task:
                self.scheduler.schedule_task(task, self.timetable)
                self.get_timetable()

        if self.scheduler.task_scheduled and self.time_to_dispatch():
            self.dispatch()
            self.scheduler.reset_schedule()

    def get_next_task_to_schedule(self):
        task_id = self.timetable.get_earliest_task_id()
        if task_id:
            task_dict = self.ccu_store.get_task(task_id)
            task = self.task_cls.from_dict(task_dict)
            return task

    def time_to_dispatch(self):
        current_time = ts.get_time_stamp()
        if current_time < self.scheduler.navigation_start_time:
            return False
        return True

    def dispatch(self):
        current_time = ts.get_time_stamp()
        print("Dispatching task at: ", current_time)









