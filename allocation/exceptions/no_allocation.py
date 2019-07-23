class NoAllocation(Exception):

    def __init__(self, round_id):
        """ Raised when no allocation was possible

        """
        Exception.__init__(self, round_id)
        self.round_id = round_id

