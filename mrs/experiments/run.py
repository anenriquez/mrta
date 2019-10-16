import argparse
import logging.config
import time

from fmlib.config.params import ConfigParams
from fmlib.db.mongo import MongoStore
from fmlib.db.mongo import MongoStoreInterface
from mrs.config.experiment import ExperimentFactory
from mrs.tests.allocation_test import Allocate
from mrs.utils.datasets import load_tasks_to_db
from mrs.utils.datasets import validate_dataset_file

ConfigParams.default_config_module = 'mrs.config.default'


class Run:

    def __init__(self, experiment_name, dataset_file, config_file=None):

        self.logger = logging.getLogger('mrs.experiment')

        self.experiment_name = experiment_name
        self.dataset_module, self.dataset_file = validate_dataset_file(experiment_name,
                                                                       dataset_file)
        if config_file is None:
            self.config_params = ConfigParams.default()
        else:
            self.config_params = ConfigParams.from_file(config_file)

        self.logger_config = self.config_params.get('logger')
        logging.config.dictConfig(self.logger_config)

        self.robot_stores = self.get_robot_stores()
        self.ccu_store = self.get_ccu_store()
        self.experiment_store = self.get_experiment_store()

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

    def get_ccu_store(self):
        ccu_store_config = self.config_params.get('ccu_store')
        ccu_store = MongoStore(**ccu_store_config)
        return ccu_store

    def get_experiment_store(self):
        port = self.config_params.get('experiment_store').get('port')
        experiment_store = MongoStore(db_name=self.experiment_name, port=port, alias=self.experiment_name)
        return experiment_store

    def clean_store(self, store):
        store_interface = MongoStoreInterface(store)
        store_interface.clean()
        self.logger.info("Store %s cleaned", store_interface._store.db_name)

    def run(self):
        for robot_store in self.robot_stores:
            self.clean_store(robot_store)
        self.clean_store(self.ccu_store)

        dataset_id, tasks = load_tasks_to_db(self.dataset_module, self.dataset_file)

        experiment = ExperimentFactory(self.experiment_store.alias, dataset_id)
        experiment(tasks=tasks)

        test = Allocate(tasks, self.logger_config)
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

    parser.add_argument('dataset_file', type=str, action='store', help='Name of the file, including extension')

    args = parser.parse_args()
    run_experiment = Run(args.experiment_name, args.dataset_file, args.file)
    run_experiment.run()


