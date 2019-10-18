import collections
from datetime import timedelta

import yaml
from fmlib.models.requests import TransportationRequest
from fmlib.models.tasks import Task
from fmlib.utils.utils import load_file_from_module
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid
from importlib_resources import contents


def get_dataset_module(experiment_name):
    """ Returns the dataset module for the experiment_name
    """
    if experiment_name == 'non_intentional_delays':
        dataset_module = 'dataset_lib.datasets.non_overlapping_tw.generic_task.random'
    elif experiment_name == 'intentional_delays':
        dataset_module = 'dataset_lib.datasets.non_overlapping_tw.generic_task.random'

    return dataset_module


def get_dataset_files(dataset_module):
    dataset_files = list()
    files = contents(dataset_module)
    for file in files:
        if file.endswith('.yaml'):
            dataset_files.append(file)

    return dataset_files


def validate_dataset_file(experiment_name, dataset_file):
    dataset_module = get_dataset_module(experiment_name)
    dataset_files = get_dataset_files(dataset_module)
    if dataset_file not in dataset_files:
        raise ValueError(dataset_file)
    return dataset_module, dataset_file


def load_yaml(file):
    """ Reads a yaml file and returns a dictionary with its contents

    :param file: file to load
    :return: data as dict()
    """
    with open(file, 'r') as file:
        data = yaml.safe_load(file)
    return data


def load_tasks_to_db(dataset_module, dataset_file):
    file = load_file_from_module(dataset_module, dataset_file)
    dataset = yaml.safe_load(file)

    tasks_dict = dataset.get('tasks')
    ordered_tasks = collections.OrderedDict(sorted(tasks_dict.items()))
    tasks = list()

    for task_id, task_info in ordered_tasks.items():
        start_location = task_info.get("start_location")
        finish_location = task_info.get("finish_location")

        earliest_start_time, latest_start_time = reference_to_current_time(task_info.get("earliest_start_time"),
                                                                           task_info.get("latest_start_time"))
        hard_constraints = task_info.get("hard_constraints")

        request = TransportationRequest(request_id=generate_uuid(), pickup_location=start_location,
                                        delivery_location=finish_location, earliest_pickup_time=earliest_start_time,
                                        latest_pickup_time=latest_start_time, hard_constraints=hard_constraints)

        task = Task.create_new(task_id=task_id, request=request)

        tasks.append(task)

    return tasks


def get_dataset_id(dataset_module, dataset_file):
    file = load_file_from_module(dataset_module, dataset_file)
    dataset = yaml.safe_load(file)
    return dataset.get('dataset_id')


def reference_to_current_time(earliest_time, latest_time):
    delta = timedelta(minutes=earliest_time)
    r_earliest_time = TimeStamp(delta).to_str()

    delta = timedelta(minutes=latest_time)
    r_latest_time = TimeStamp(delta).to_str()

    return r_earliest_time, r_latest_time


def flatten_dict(dict_input):
    """ Returns a dictionary without nested dictionaries

    :param dict_input: nested dictionary
    :return: flattened dictionary

    """
    flattened_dict = dict()

    for key, value in dict_input.items():
        if isinstance(value, dict):
            new_keys = sorted(value.keys())
            for new_key in new_keys:
                entry = {key + '_' + new_key: value[new_key]}
                flattened_dict.update(entry)
        else:
            entry = {key: value}
            flattened_dict.update(entry)

    return flattened_dict
