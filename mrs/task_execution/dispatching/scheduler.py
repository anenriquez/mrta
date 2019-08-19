import logging
from mrs.exceptions.task_execution import InconsistentSchedule
from mrs.structs.task import TaskStatus
from mrs.db_interface import DBInterface


class Scheduler(object):

    def __init__(self, ccu_store, stp):
        self.db_interface = DBInterface(ccu_store)
        self.stp = stp
        self.navigation_start_time = -float('inf')  # of scheduled task

    def schedule_task(self, task, navigation_start,  timetable):
        print("Dispatchable graph:", timetable.dispatchable_graph)

        try:
            self.assign_timepoint(task, navigation_start, timetable)
        except InconsistentSchedule as e:
            logging.exception("Task %s could not be scheduled.", e.task)
            raise InconsistentSchedule(e.task)

    def assign_timepoint(self, task, navigation_start, timetable):

        timetable.dispatchable_graph.assign_timepoint(navigation_start)
        minimal_network = self.stp.propagate_constraints(timetable.dispatchable_graph)

        if minimal_network:
            print("The assignment is consistent")
            print("Dispatchable graph:", timetable.dispatchable_graph)

            timetable.get_schedule(task.id)

            print("Schedule: ", timetable.schedule)

            self.db_interface.update_timetable(timetable)
            self.db_interface.update_task_status(task, TaskStatus.SCHEDULED)
            self.navigation_start_time = navigation_start

        else:
            raise InconsistentSchedule(task)

    def reallocate(self):
        pass

    def reset_schedule(self, timetable):
        timetable.remove_task()
        self.db_interface.update_timetable(timetable)
