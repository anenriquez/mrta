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
               'tessi-drea': ['re-allocate'],
               'tessi-dsc': ['re-allocate']
               }

    def __init__(self, name, allocation_method):
        super().__init__(name, allocation_method)


class Preventive(Reaction):

    """ Maps allocation methods with their available preventive measures """

    actions = {'tessi': ['re-allocate'],
               'tessi-srea': ['re-allocate', 're-schedule'],
               'tessi-drea': ['re-allocate', 're-schedule'],
               'tessi-dsc': ['re-allocate']
               }

    def __init__(self, name, allocation_method):
        super().__init__(name, allocation_method)


class DelayManagement:

    def __init__(self, reaction_name, reaction_type, allocation_method):
        if reaction_type == "preventive":
            self.reaction = Preventive(reaction_name, allocation_method)
        elif reaction_type == "corrective":
            self.reaction = Corrective(reaction_name, allocation_method)
        else:
            self.reaction = None
