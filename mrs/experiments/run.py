import argparse
import logging.config
import time

from fmlib.config.params import ConfigParams
from fmlib.db.mongo import MongoStore
from fmlib.db.mongo import MongoStoreInterface
from importlib_resources import contents

from mrs.db.models.performance.experiment import Experiment
from mrs.tests.allocation_test import Allocate
from mrs.utils.datasets import load_tasks_to_db

ConfigParams.default_config_module = 'mrs.config.default'


class MRTAExperiment:

    experiments = ['non_intentional_delays',
                   'intentional_delays',
                   'task_scalability',
                   'robot_scalability']

    def __init__(self, experiment_name, config_file=None):

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

        if experiment_name not in MRTAExperiment.experiments:
            self.logger.error("%s is not a valid experiment name", experiment_name)
            raise ValueError(experiment_name)
        self.experiment_name = experiment_name

        port = self.config_params.get('experiment_store').get('port')
        self.db = MongoStore(db_name=experiment_name, port=port, alias=experiment_name)

        self.logger.info("Starting experiment % s", self.experiment_name)

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

    def get_dataset_module(self):
        """ Returns the dataset module for the experiment_name
        """
        if self.experiment_name == 'non_intentional_delays':
            dataset_module = 'dataset_lib.datasets.non_overlapping_tw.generic_task.random'
        elif self.experiment_name == 'intentional_delays':
            dataset_module = 'dataset_lib.datasets.non_overlapping_tw.generic_task.random'

        return dataset_module

    @staticmethod
    def get_dataset_files(dataset_module):
        dataset_files = list()
        files = contents(dataset_module)
        for file in files:
            if file.endswith('.yaml'):
                dataset_files.append(file)

        return dataset_files

    def run_all(self):
        dataset_module = self.get_dataset_module()
        dataset_files = self.get_dataset_files(dataset_module)

        for dataset_file in dataset_files:
            self.logger.info("Dataset file: %s", dataset_file)

            for robot_store in self.robot_stores:
                self.clean_store(robot_store)

            self.clean_store(self.ccu_store)

            dataset_id, tasks = load_tasks_to_db(dataset_module, dataset_file)

            Experiment.set_meta_info(self.experiment_name, dataset_id)

            run_id = Experiment.get_next_run_id(self.experiment_name, dataset_id)

            Experiment.create(run_id=run_id,
                              dataset_id=dataset_id, tasks=tasks,
                              connection_alias=self.experiment_name,
                              collection_name=dataset_id)
            self.run(tasks)

    def run(self, tasks):
        logger_config = self.config_params.get('logger')

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

    experiment = MRTAExperiment(args.experiment_name, args.file)

    experiment.run_all()



