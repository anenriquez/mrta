import logging

from ropod.structs.status import ActionStatus


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

    def recover(self, timetable, task, is_consistent):
        next_task = timetable.get_next_task(task)

        if next_task and (self.name == "re-allocate" and self.is_next_task_late(timetable, task, next_task)) \
                or self.name.startswith("re-schedule") \
                or next_task and self.name == "abort" and self.is_next_task_late(timetable, task, next_task):
            return True
        return False

    def is_next_task_late(self, timetable, task, next_task):
        last_completed_action = None
        mean = 0
        variance = 0

        for action_progress in task.status.progress.actions:
            if action_progress.status == ActionStatus.COMPLETED:
                last_completed_action = action_progress.action

            elif action_progress.status == ActionStatus.ONGOING or action_progress.status == ActionStatus.PLANNED:
                mean += action_progress.action.estimated_duration.mean
                variance += action_progress.action.estimated_duration.variance

        estimated_duration = mean + 2*round(variance ** 0.5, 3)
        self.logger.debug("Remaining estimated task duration: %s ", estimated_duration)

        if last_completed_action:
            start_node, finish_node = last_completed_action.get_node_names()
            last_time = timetable.stn.get_time(task.task_id, finish_node)
        else:
            last_time = timetable.stn.get_time(task.task_id, 'start')

        estimated_start_time = last_time + estimated_duration
        self.logger.debug("Estimated start time of next task: %s ", estimated_start_time)

        latest_start_time = timetable.dispatchable_graph.get_time(next_task.task_id, 'start', False)
        self.logger.debug("Latest permitted start time of next task: %s ", latest_start_time)

        if latest_start_time < estimated_start_time:
            self.logger.debug("Next task is at risk")
            return True
        else:
            self.logger.debug("Next task is NOT at risk")
            return False


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

    def recover(self, timetable, task, is_consistent):
        """ React only if the last assignment was inconsistent
        """
        if is_consistent:
            return False
        elif not is_consistent and super().recover(timetable, task, is_consistent):
            return True


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

    def recover(self, timetable, task, is_consistent):
        """ React both, when the last assignment was consistent and when it was inconsistent
        """
        return super().recover(timetable, task, is_consistent)


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
