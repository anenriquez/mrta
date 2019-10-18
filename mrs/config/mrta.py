from mrs.task_allocation.auctioneer import Auctioneer
from mrs.task_execution.dispatcher import Dispatcher
from mrs.task_allocation.bidder import Bidder
from mrs.task_execution.schedule_monitor import ScheduleMonitor
import logging
from stn.stp import STP
from fmlib.db.mongo import MongoStore
from mrs.utils.datasets import get_dataset_id
from mrs.utils.datasets import load_tasks_to_db
from mrs.config.experiment import ExperimentFactory


class MRTAFactory:

    """ Maps an allocation method to its stp_solver solver """
    allocation_methods = {'tessi': 'fpc',
                          'tessi-srea': 'srea',
                          'tessi-dsc': 'dsc'
                          }

    def __init__(self, allocation_method, **kwargs):
        """
            Registers and creates MRTA (multi-robot task allocation) components

            Args:

                allocation_method(str): name of the allocation method

        """

        self.logger = logging.getLogger('mrta.config.components')
        self.allocation_method = allocation_method

        experiment_config = kwargs.get('experiment_config')
        if experiment_config:
            self.experiment = self.configure_experiment(**experiment_config)
        else:
            self.experiment = None

        self._components = {}

        stp_solver_name = self.allocation_methods.get(allocation_method)
        if not stp_solver_name:
            self.logger.error("The given allocation method is not available")
            raise ValueError(allocation_method)

        self.stp_solver = STP(stp_solver_name)

        self.register_component('auctioneer', Auctioneer)
        self.register_component('dispatcher', Dispatcher)
        self.register_component('bidder', Bidder)
        self.register_component('schedule_monitor', ScheduleMonitor)

    def register_component(self, component_name, component):
        self._components[component_name] = component

    @staticmethod
    def configure_experiment(experiment_name, port, dataset_module, dataset_file, new_run=True):
        experiment_store = MongoStore(db_name=experiment_name, port=port, alias=experiment_name)
        dataset_id = get_dataset_id(dataset_module, dataset_file)
        tasks = load_tasks_to_db(dataset_module, dataset_file)
        experiment_factory = ExperimentFactory(experiment_store.alias, dataset_id, new_run)
        experiment_factory(tasks=tasks)
        return experiment_factory.experiment

    def __call__(self, **kwargs):
        components = dict()

        for component_name, configuration in kwargs.items():
            self.logger.debug("Creating %s", component_name)
            component = self._components.get(component_name)

            if component:
                _instance = component(allocation_method=self.allocation_method,
                                      stp_solver=self.stp_solver,
                                      experiment=self.experiment,
                                      **configuration)
                components[component_name] = _instance

        return components

