import collections
from datetime import timedelta

import yaml
from ropod.utils.timestamp import TimeStamp

from mrs.config.task_factory import TaskFactory


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
    task_type = dataset_dict.get('task_type')

    task_factory = TaskFactory()
    task_cls = task_factory.get_task_cls(task_type)

    tasks = list()
    tasks_dict = dataset_dict.get('tasks')
    ordered_tasks = collections.OrderedDict(sorted(tasks_dict.items()))

    for task_id, task_info in ordered_tasks.items():
        task_dict = reference_to_current_time(task_info)
        task = task_cls.from_dict(task_dict)
        tasks.append(task)

    return tasks


def reference_to_current_time(task_dict):
    est = task_dict['earliest_start_time']
    delta = timedelta(minutes=est)
    task_dict.update({'earliest_start_time': TimeStamp(delta).to_str()})

    lst = task_dict['latest_start_time']
    delta = timedelta(minutes=lst)
    task_dict.update({'latest_start_time': TimeStamp(delta).to_str()})

    return task_dict


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
