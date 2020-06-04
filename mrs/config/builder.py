import logging

from mrs.allocation.auctioneer import Auctioneer
from mrs.allocation.bidder import Bidder
from mrs.execution.dispatcher import Dispatcher
from mrs.execution.delay_recovery import DelayRecovery
from mrs.execution.executor import Executor
from mrs.execution.fleet_monitor import FleetMonitor
from mrs.execution.schedule_execution_monitor import ScheduleExecutionMonitor
from mrs.execution.scheduler import Scheduler
from mrs.performance.tracker import PerformanceTracker
from mrs.simulation.simulator import Simulator
from mrs.timetable.timetable import Timetable, TimetableManager
from mrs.timetable.monitor import TimetableMonitor
from stn.stp import STP


class MRTABuilder:

    _component_modules = {'simulator': Simulator,
                          'timetable': Timetable,
                          'timetable_manager': TimetableManager,
                          'delay_recovery': DelayRecovery,
                          'auctioneer': Auctioneer,
                          'fleet_monitor': FleetMonitor,
                          'dispatcher': Dispatcher,
                          'bidder': Bidder,
                          'executor': Executor,
                          'scheduler': Scheduler,
                          'schedule_execution_monitor': ScheduleExecutionMonitor,
                          'timetable_monitor': TimetableMonitor,
                          'performance_tracker': PerformanceTracker,
                          }

    _config_order = ['simulator',
                     'timetable',
                     'timetable_manager',
                     'delay_recovery',
                     'auctioneer',
                     'fleet_monitor',
                     'dispatcher',
                     'bidder',
                     'executor',
                     'scheduler',
                     'schedule_execution_monitor',
                     'timetable_monitor',
                     'performance_tracker',
                     ]

    """ Maps an allocation method to its stp_solver solver """
    _allocation_methods = {'tessi': 'fpc',
                           'tessi-srea': 'srea',
                           'tessi-dsc': 'dsc',
                           }

    def __init__(self, allocation_method, **kwargs):
        """
            Registers and creates MRTA (multi-robot task allocation) components

            Args:

                allocation_method(str): name of the allocation method

        """

        self.logger = logging.getLogger('mrta.config.components')
        self._components = dict()
        self._component_modules = kwargs.get('component_modules', self._component_modules)
        self.config_order = kwargs.get('config_order', self._config_order)

        self.register_component('allocation_method', allocation_method)
        self.register_component('stp_solver', self.get_stp_solver())

    def register_component(self, component_name, component):
        self._components[component_name] = component

    def get_stp_solver(self):
        allocation_method = self._components.get('allocation_method')
        solver_name = self._allocation_methods.get(allocation_method)
        if not solver_name:
            self.logger.error("The given allocation method is not available")
            raise ValueError(allocation_method)
        return STP(solver_name)

    def configure_component(self, component_name, config, **kwargs):
        self.logger.debug("Creating %s", component_name)
        component = self._component_modules.get(component_name)

        if component and isinstance(config, dict):
            self.register_component(component_name, component)
            _component = component(**config, **self._components, **kwargs)
            return _component

    def __call__(self, **kwargs):
        d_graph_watchdog = kwargs.get("d_graph_watchdog", False)
        for component_name in self.config_order:
            if component_name in self._component_modules:
                component_config = kwargs.get(component_name, dict())
                component = self.configure_component(component_name, component_config, d_graph_watchdog=d_graph_watchdog)
                self._components[component_name] = component
        return self._components
