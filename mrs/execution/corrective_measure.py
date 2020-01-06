import logging


class CorrectiveMeasure:

    """ Maps allocation methods with their available corrective measures """

    corrective_measures = {'tessi': ['pre-failure-re-allocate'],
                           'tessi-srea': ['post-failure-re-allocate', 'pre-failure-re-allocate'],
                           'tessi-drea': ['pre-failure-re-schedule'],
                           'tessi-dsc': ['post-failure-re-allocate']
                           }

    def __init__(self, name, allocation_method):
        self.logger = logging.getLogger('mrs.corrective.measures')
        self.name = self.validate_name(name, allocation_method)

    def validate_name(self, name, allocation_method):
        available_names = self.corrective_measures.get(allocation_method)
        if name not in available_names:
            self.logger.error("Corrective measure %s is not available for method %s", name, allocation_method)
            raise ValueError(name)
        return name

