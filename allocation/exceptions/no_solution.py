class NoSolution(Exception):

    def __init__(self):
        """ Raised when the stp solver cannot produce a solution for the problem
        """
        Exception.__init__(self)

