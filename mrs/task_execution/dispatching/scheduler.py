import logging


class Scheduler(object):

    def __init__(self, ccu_store, stp):
        self.ccu_store = ccu_store
        self.stp = stp
        self.navigation_start_time = -float('inf')  # of scheduled task

    def schedule_task(self, task, timetable):
        print("Dispatchable graph:", timetable.dispatchable_graph)

        navigation_start = timetable.dispatchable_graph.get_task_navigation_start_time(task.id)
        self.assign_timepoint(task, timetable, navigation_start)

    def assign_timepoint(self, task, timetable, navigation_start):

        timetable.dispatchable_graph.assign_timepoint(navigation_start)
        minimal_network = self.stp.propagate_constraints(timetable.dispatchable_graph)

        if minimal_network:
            print("The assignment is consistent")
            print("Dispatchable graph:", timetable.dispatchable_graph)

            timetable.get_schedule(task.id)

            print("Schedule: ", timetable.schedule)

            self.ccu_store.update_timetable(timetable)
            self.update_task_status(task, 3)  # 3 is SCHEDULED
            self.navigation_start_time = navigation_start

        else:
            self.reallocate()

    def reallocate(self):
        pass

    def update_task_status(self, task, status):
        task.status.status = status
        logging.debug("Updating task status to %s", task.status.status)
        self.ccu_store.update_task(task)

    def reset_schedule(self, timetable):
        timetable.schedule = self.stp.get_stn()
        self.ccu_store.update_timetable(timetable)
