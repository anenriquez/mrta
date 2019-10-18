import argparse
import logging.config
import time

from fmlib.api import API
from fmlib.config.builders import Store
from fmlib.config.params import ConfigParams
from fmlib.models.tasks import Task
from mrs.config.mrta import MRTAFactory
from mrs.utils.datasets import validate_dataset_file
from ropod.structs.task import TaskStatus as TaskStatusConst

ConfigParams.default_config_module = 'mrs.config.default'


class MRS(object):
    def __init__(self, experiment_name, dataset_file, config_file=None):

        self.logger = logging.getLogger('mrs')

        self.experiment_name = experiment_name
        self.dataset_module, self.dataset_file = validate_dataset_file(experiment_name,
                                                                       dataset_file)
        if config_file is None:
            self.config_params = ConfigParams.default()
        else:
            self.config_params = ConfigParams.from_file(config_file)

        logger_config = self.config_params.get('logger')
        logging.config.dictConfig(logger_config)

        self.api = self.get_api()
        self.ccu_store = self.get_ccu_store()
        self.experiment_config = self.get_experiment_config()

        components = self.get_mrta_components()
        self.auctioneer = components.get('auctioneer')
        self.dispatcher = components.get('dispatcher')

        self.api.register_callbacks(self)
        self.logger.info("Initialized MRS")

    def get_api(self):
        api_config = self.config_params.get('api')
        return API(**api_config)

    def get_ccu_store(self):
        store_config = self.config_params.get('ccu_store')
        return Store(**store_config)

    def get_experiment_config(self):
        experiment_config = {'experiment_name': self.experiment_name,
                             'port': self.config_params.get('experiment_store').get('port'),
                             'dataset_module': self.dataset_module,
                             'dataset_file': self.dataset_file}
        return experiment_config

    def get_mrta_components(self):
        allocation_method = self.config_params.get('allocation_method')
        fleet = self.config_params.get('resource_manager').get('resources').get('fleet')
        mrta_factory = MRTAFactory(allocation_method, fleet, experiment_config=self.experiment_config)

        config = self.config_params.get('plugins').get('mrta')
        components = mrta_factory(**config)

        for component_name, component in components.items():
            if hasattr(component, 'configure'):
                self.logger.debug("Configuring %s", component_name)
                component.configure(api=self.api, ccu_store=self.ccu_store)

        return components

    def start_test_cb(self, msg):
        self.logger.debug("Start test msg received")
        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        self.auctioneer.allocate(tasks)

    def run(self):
        try:
            self.api.start()

            while True:
                self.auctioneer.run()
                self.api.run()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.api.shutdown()
            self.logger.info('FMS is shutting down')

    def shutdown(self):
        self.api.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')

    parser.add_argument('experiment_name', type=str, action='store', help='Name of the experiment',
                        choices=['non_intentional_delays',
                                 'intentional_delays'])

    parser.add_argument('dataset_file', type=str, action='store', help='Name of the file, including extension')

    args = parser.parse_args()
    mrs = MRS(args.experiment_name, args.dataset_file, args.file)
    mrs.run()
