import logging


class Reaction:

    actions = {}

    def __init__(self, name, allocation_method):
        self.logger = logging.getLogger('mrs.corrective.measures')
        self.name = self.validate_name(name, allocation_method)

    def validate_name(self, name, allocation_method):
        available_names = self.actions.get(allocation_method)
        if name not in available_names:
            self.logger.error("Measure %s is not available for method %s", name, allocation_method)
            raise ValueError(name)
        return name


class Corrective(Reaction):

    """ Maps allocation methods with their available corrective measures """

    actions = {'tessi': ['re-allocate'],
               'tessi-srea': ['re-allocate'],
               'tessi-dsc': ['re-allocate']
               }

    def __init__(self, name, allocation_method):
        super().__init__(name, allocation_method)


class Preventive(Reaction):

    """ Maps allocation methods with their available preventive measures """

    actions = {'tessi': ['re-allocate'],
               'tessi-srea': ['re-allocate', 're-schedule'],
               'tessi-dsc': ['re-allocate']
               }

    def __init__(self, name, allocation_method):
        super().__init__(name, allocation_method)


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


class DelayManagement:
    def __init__(self, reaction_type, reaction_name, allocation_method):
        try:
            reaction_cls = reaction_factory.get_reaction(reaction_type)
            self.reaction = reaction_cls(reaction_name, allocation_method)
        except ValueError:
            self.reaction = None
