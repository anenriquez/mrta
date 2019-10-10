from fmlib.config.params import ConfigParams
from importlib_resources import contents
from fmlib.db.mongo import MongoStore
import argparse
from mrs.tests.allocation_test import AllocationTest
import time

ConfigParams.default_config_module = 'mrs.config.default'

experiment_names = ["non_intentional_delays",
                    "intentional_delays",
                    "task_scalability",
                    "robot_scalability"]


class MRTAExperiment:
    def __init__(self, experiment_name, config_file=None):

        if experiment_name not in experiment_names:
            raise ValueError(experiment_name)

        self.experiment_name = experiment_name

        if config_file is None:
            self.config_params = ConfigParams.default()
        else:
            self.config_params = ConfigParams.from_file(config_file)

        self.db = MongoStore(db_name=experiment_name, alias=experiment_name)

        # TODO: Keep track of number of runs for each experiment name
        self.db_collection = experiment_name + '_1'

    def get_dataset_module(self):
        """ Returns the dataset module for the experiment_name
        """
        if self.experiment_name == 'non_intentional_delays':
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
            self.run(dataset_module, dataset_file)

    def run(self, dataset_module, dataset_file):

        fleet = self.config_params.get('resource_manager').get('resources').get('fleet')
        ccu_store = self.config_params.get("ccu_store")
        robot_store = self.config_params.get('robot_proxy').get("robot_store")

        print("Fleet: ", fleet)
        print("ccu_store: ", ccu_store)
        test = AllocationTest(dataset_module, dataset_file,
                              fleet=fleet,
                              ccu_store=ccu_store,
                              robot_store=robot_store)
        test.start()
        timeout_duration = 300  # 5 minutes
        try:
            time.sleep(5)
            start_time = time.time()
            test.trigger()
            while not test.terminated and start_time + timeout_duration > time.time():
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            print('Task request test interrupted; exiting')

        print("Exiting test...")
        test.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')

    parser.add_argument('experiment_name', type=str, action='store', help='Name of the experiment',
                        choices=['non_intentional_delays'])
    args = parser.parse_args()

    experiment = MRTAExperiment(args.experiment_name, args.file)

    experiment.run_all()




