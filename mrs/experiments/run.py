import argparse
import time

from mrs.tests.allocation_test import AllocationTest
from sacred import Experiment
from sacred import SETTINGS
from sacred.observers import MongoObserver

SETTINGS.CONFIG.READ_ONLY_CONFIG = False

ex = Experiment()
ex.observers.append(MongoObserver.create())


def process_arguments(args):
    global ex
    config_file = args.file
    experiment_name = args.experiment_name
    dataset_module, dataset_files = get_datasets(experiment_name)

    ex.add_config(config_file)
    ex.add_config(dataset_module=dataset_module)

    return dataset_module, dataset_files


def get_datasets(experiment_name):
    # TODO: Get datasets based on experiment.
    dataset_module = 'dataset_lib.datasets.non_overlapping_tw.generic_task.random'
    dataset_files = list()
    dataset_files.append('non_overlapping_1.yaml')
    return dataset_module, dataset_files


@ex.main
def run(dataset_module, dataset_file, resource_manager, ccu_store, robot_proxy):
    timeout_duration = 300  # 5 minutes

    fleet = resource_manager.get('resources').get('fleet')
    robot_store = robot_proxy.get("robot_store")

    test = AllocationTest(dataset_module, dataset_file,
                          fleet=fleet,
                          ccu_store=ccu_store,
                          robot_store=robot_store)
    test.start()
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
    parser.add_argument('--file', type=str, action='store', help='Path to the config file',
                        default='../config/default/config.yaml')
    parser.add_argument('experiment_name', type=str, action='store', help='Name of the experiment',
                        choices=['non_intentional_delays'])

    dataset_module, dataset_files = process_arguments(parser.parse_args())

    for dataset_file in dataset_files:
        r = ex.run(config_updates={'dataset_file': dataset_file})


