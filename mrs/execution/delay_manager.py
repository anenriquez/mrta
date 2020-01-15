import logging

from ropod.structs.status import ActionStatus


class Reaction:

    options = ["re-allocate", "re-schedule", "abort"]

    def __init__(self, name):
        self.logger = logging.getLogger('mrs.reaction')
        self.name = self.validate_name(name)

    def validate_name(self, name):
        if name not in self.options:
            self.logger.error("Reaction %s is not available", name)
            raise ValueError(name)
        return name

    def react(self, timetable, task, last_assignment):
        next_task = timetable.get_next_task(task)

        if next_task and (self.name == "re-allocate" and self.is_next_task_late(timetable, task, next_task)) \
                or self.name == "re-schedule" \
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


class Corrective(Reaction):

    """ Maps allocation methods with their available corrective measures """

    reactions = {'tessi': ["re-allocate", "abort"],
                 'tessi-srea': ["re-allocate", "abort"],
                 'tessi-dsc': ["re-allocate", "abort"],
                 }

    def __init__(self, name, allocation_method):
        super().__init__(name)
        if self.name not in self.reactions.get(allocation_method):
            raise ValueError(name)

    def react(self, timetable, task, last_assignment):
        """ React only if the last assignment was inconsistent
        """
        if last_assignment.is_consistent:
            return False
        elif not last_assignment.is_consistent and super().react(timetable, task, last_assignment):
            return True


class Preventive(Reaction):

    """ Maps allocation methods with their available preventive measures """

    reactions = {'tessi': ["re-allocate", "abort"],
                 'tessi-srea': ["re-allocate", "re-schedule", "abort"],
                 'tessi-dsc': ["re-allocate", "abort"],
                 }

    def __init__(self, name, allocation_method):
        super().__init__(name)
        if self.name not in self.reactions.get(allocation_method):
            raise ValueError(name)

    def react(self, timetable, task, last_assignment):
        """ React both, when the last_assignment was consistent and when it was inconsistent
        """
        return super().react(timetable, task, last_assignment)


class ReactionFactory:

    def __init__(self):
        self._reactions = dict()

    def register_reaction(self, reaction_type, reaction):
        self._reactions[reaction_type] = reaction

    def get_reaction(self, reaction_type):
        reaction = self._reactions.get(reaction_type)
        if not reaction:
            raise ValueError(reaction_type)
        return reaction


reaction_factory = ReactionFactory()
reaction_factory.register_reaction('corrective', Corrective)
reaction_factory.register_reaction('preventive', Preventive)


class DelayManager:
    def __init__(self, timetable, reaction_type, reaction_name, allocation_method):
        self.timetable = timetable
        try:
            reaction_cls = reaction_factory.get_reaction(reaction_type)
            self.reaction = reaction_cls(reaction_name, allocation_method)
        except ValueError:
            self.logger.error("Reaction type %s is not available", reaction_type)

        self.logger = logging.getLogger('mrs.delay.manager.%s' % self.timetable.robot_id)
        self.logger.debug("DelayManager initialized %s", self.timetable.robot_id)

    def react(self, task, last_assignment):
        """ React to a possible delay:
            - apply a reaction (preventive or corrective)
            - if no reaction is configured and the current task is inconsistent, abort the next task.

        A preventive reaction prevents delay of next_task. Applied BEFORE current task becomes inconsistent
        A corrective reaction prevents delay of next task. Applied AFTER current task becomes inconsistent

        task (Task) : current task
        last_assignment (Assignment): last assignment
        """

        return self.reaction.react(self.timetable, task, last_assignment)
