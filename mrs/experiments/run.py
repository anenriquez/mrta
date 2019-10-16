import argparse
import logging.config
import time

from fmlib.config.params import ConfigParams
from fmlib.db.mongo import MongoStore
from fmlib.db.mongo import MongoStoreInterface
from mrs.config.experiment import ExperimentFactory
from mrs.tests.allocation_test import Allocate
from mrs.utils.datasets import get_dataset_files
from mrs.utils.datasets import get_dataset_module
from mrs.utils.datasets import load_tasks_to_db

ConfigParams.default_config_module = 'mrs.config.default'


class Run:

    def __init__(self, experiment_name, config_file=None):

        self.experiment_name = experiment_name

        self.logger = logging.getLogger('mrs.experiment')

        if config_file is None:
            self.config_params = ConfigParams.default()
        else:
            self.config_params = ConfigParams.from_file(config_file)

        logger_config = self.config_params.get('logger')
        logging.config.dictConfig(logger_config)

        self.robot_stores = self.get_robot_stores()
        ccu_store_config = self.config_params.get('ccu_store')
        self.ccu_store = MongoStore(**ccu_store_config)

        port = self.config_params.get('experiment_store').get('port')
        self.db = MongoStore(db_name=experiment_name, port=port, alias=experiment_name)

        self.logger.info("Running experiment % s", self.experiment_name)

    def get_robot_stores(self):
        robot_stores = list()

        fleet = self.config_params.get('resource_manager').get('resources').get('fleet')
        robot_store_config = self.config_params.get('robot_proxy').get("robot_store")

        for robot_id in fleet:
            robot_store_config.update({'db_name': 'robot_store_' + robot_id.split('_')[1]})
            robot_store = MongoStore(**robot_store_config)
            robot_stores.append(robot_store)
        return robot_stores

    def clean_store(self, store):
        store_interface = MongoStoreInterface(store)
        store_interface.clean()
        self.logger.info("Store %s cleaned", store_interface._store.db_name)

    def run_all(self):
        dataset_module = get_dataset_module(self.experiment_name)
        dataset_files = get_dataset_files(dataset_module)

        for dataset_file in dataset_files:
            self.logger.info("Dataset file: %s", dataset_file)

            for robot_store in self.robot_stores:
                self.clean_store(robot_store)
            self.clean_store(self.ccu_store)

            dataset_id, tasks = load_tasks_to_db(dataset_module, dataset_file)
            self.run(dataset_id, tasks)

    def run(self, dataset_id, tasks):
        logger_config = self.config_params.get('logger')

        experiment = ExperimentFactory(self.db.alias, dataset_id)
        experiment(tasks=tasks)

        test = Allocate(tasks, logger_config)
        test.start()

        try:
            time.sleep(5)
            test.trigger()
            while not test.terminated:
                time.sleep(0.5)

        except (KeyboardInterrupt, SystemExit):
            print('Task request test interrupted; exiting')

        print("Exiting test...")
        test.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')

    parser.add_argument('experiment_name', type=str, action='store', help='Name of the experiment',
                        choices=['non_intentional_delays',
                                 'intentional_delays'])
    args = parser.parse_args()
    run_experiment = Run(args.experiment_name, args.file)
    run_experiment.run_all()


