import collections
from datetime import timedelta

import yaml
from ropod.utils.timestamp import TimeStamp

from mrs.db.models.task import Task, TaskLot


def load_yaml(file):
    """ Reads a yaml file and returns a dictionary with its contents

    :param file: file to load
    :return: data as dict()
    """
    with open(file, 'r') as file:
        data = yaml.safe_load(file)
    return data


def load_yaml_dataset(dataset_path):
    dataset_dict = load_yaml(dataset_path)

    tasks = list()
    tasks_dict = dataset_dict.get('tasks')
    ordered_tasks = collections.OrderedDict(sorted(tasks_dict.items()))

    for task_id, task_info in ordered_tasks.items():
        start_location = task_info.get("start_location")
        finish_location = task_info.get("finish_location")

        earliest_start_time, latest_start_time = reference_to_current_time(task_info.get("earliest_start_time"),
                                                                           task_info.get("latest_start_time"))
        hard_constraints = task_info.get("hard_constraints")

        TaskLot.create(task_id, start_location, finish_location, earliest_start_time, latest_start_time, hard_constraints)
        task = Task.create(task_id)

        tasks.append(task)

    return tasks


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
