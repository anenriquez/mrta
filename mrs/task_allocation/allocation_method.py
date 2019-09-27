class AllocationMethod(object):
    """ Registers an allocation method with its stp solver name

    """
    def __init__(self):
        self._allocation_methods = {}

    def register_method(self, method_name, stp_solver_name):
        self._allocation_methods[method_name] = stp_solver_name

    def get_stp_solver(self, method_name):
        solver_name = self._allocation_methods.get(method_name)
        if not solver_name:
            raise ValueError(method_name)
        return solver_name


allocation_method_factory = AllocationMethod()
allocation_method_factory.register_method('tessi', 'fpc')
allocation_method_factory.register_method('tessi-srea', 'srea')
allocation_method_factory.register_method('tessi-dsc', 'dsc')