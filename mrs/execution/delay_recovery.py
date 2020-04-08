import logging

from stn.exceptions.stp import NoSTPSolution


class RecoveryMethod:

    options = ["re-allocate", "re-schedule-re-allocate", "re-schedule-abort", "abort"]

    def __init__(self, name):
        self.logger = logging.getLogger('mrs.recovery.method')
        self.name = self.validate_name(name)

    def validate_name(self, name):
        if name not in self.options:
            self.logger.error("Reaction %s is not available", name)
            raise ValueError(name)
        return name

    # def recover(self, timetable, task, task_progress, r_assigned_time, is_consistent=True):
    #     """ Returns list of tasks to recover """
    #     tasks_to_recover = list()
    #
    #     if self.name == "re-allocate" or self.name == "abort":
    #         tasks_to_recover = timetable.get_late_tasks(task, task_progress, r_assigned_time)
    #     elif "re-schedule" in self.name:
    #         # try:
    #         #     timetable.compute_dispatchable_graph(timetable.stn)
    #         #     self.logger.debug("Dispatchable graph robot %s: %s", timetable.robot_id, timetable.dispatchable_graph)
    #         # except NoSTPSolution:
    #         tasks_to_recover = timetable.get_invalid_tasks(task, r_assigned_time)
    #
    #
    #     return tasks_to_recover


class Corrective(RecoveryMethod):

    """ Maps allocation methods with their available corrective measures """

    reactions = {'tessi': ["re-allocate", "abort"],
                 'tessi-srea': ["re-allocate", "abort"],
                 'tessi-dsc': ["re-allocate", "abort"],
                 }

    def __init__(self, name, allocation_method):
        super().__init__(name)
        if self.name not in self.reactions.get(allocation_method):
            raise ValueError(name)

    def recover(self, timetable, task, task_progress, r_assigned_time, is_consistent=False):
        """ React only if the last assignment was inconsistent
        """
        tasks_to_recover = list()
        if not is_consistent:
            tasks_to_recover = timetable.get_invalid_tasks(task, r_assigned_time)
        return tasks_to_recover

        # if is_consistent:
        #     return tasks_to_recover
        # elif not is_consistent:
        #    tasks_to_recover = timetable.get_late_tasks(task, task_progress, r_assigned_time)

           # return super().recover(timetable, task, task_progress, r_assigned_time, is_consistent)


class Preventive(RecoveryMethod):

    """ Maps allocation methods with their available preventive measures """

    reactions = {'tessi': ["re-allocate", "abort"],
                 'tessi-srea': ["re-allocate", "re-schedule-re-allocate", "re-schedule-abort", "abort"],
                 'tessi-dsc': ["re-allocate", "abort"],
                 }

    def __init__(self, name, allocation_method):
        super().__init__(name)
        if self.name not in self.reactions.get(allocation_method):
            raise ValueError(name)

    def recover(self, timetable, task, task_progress, r_assigned_time, is_consistent=False):
        """ React both, when the last assignment was consistent and when it was inconsistent
        """
        if not is_consistent:
            tasks_to_recover = timetable.get_invalid_tasks(task, r_assigned_time)
        else:
            tasks_to_recover = timetable.get_late_tasks(task, task_progress, r_assigned_time)
        return tasks_to_recover
        # return super().recover(timetable, task, task_progress, r_assigned_time, is_consistent)


class RecoveryMethodFactory:

    def __init__(self):
        self._recovery_methods = dict()

    def register_recovery_method(self, recovery_type, recovery_method):
        self._recovery_methods[recovery_type] = recovery_method

    def get_recovery_method(self, recovery_type):
        recovery_method = self._recovery_methods.get(recovery_type)
        if not recovery_method:
            raise ValueError(recovery_type)
        return recovery_method


recovery_method_factory = RecoveryMethodFactory()
recovery_method_factory.register_recovery_method('corrective', Corrective)
recovery_method_factory.register_recovery_method('preventive', Preventive)


class DelayRecovery:
    def __init__(self, allocation_method, type_, method, **kwargs):
        cls_ = recovery_method_factory.get_recovery_method(type_)
        self.method = cls_(method, allocation_method)
