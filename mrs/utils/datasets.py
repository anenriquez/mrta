import collections
from datetime import timedelta

import yaml
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid

from fmlib.models.tasks import Task, TaskRequest
from mrs.db.models.task import TaskLot
from mrs.db.models.performance.task import TaskPerformance
from mrs.db.models.performance.dataset import DatasetPerformance


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
    dataset_id = dataset_dict.get('dataset_id')

    tasks_performance = list()
    tasks_dict = dataset_dict.get('tasks')
    ordered_tasks = collections.OrderedDict(sorted(tasks_dict.items()))

    for task_id, task_info in ordered_tasks.items():
        start_location = task_info.get("start_location")
        finish_location = task_info.get("finish_location")

        earliest_start_time, latest_start_time = reference_to_current_time(task_info.get("earliest_start_time"),
                                                                           task_info.get("latest_start_time"))
        hard_constraints = task_info.get("hard_constraints")

        request = TaskRequest(request_id=generate_uuid(), pickup_location=start_location,
                              delivery_location=finish_location, earliest_pickup_time=earliest_start_time,
                              latest_pickup_time=latest_start_time, hard_constraints=hard_constraints)

        task = Task.create_new(task_id=task_id, request=request)

    #     TaskLot.create(task_id, start_location, finish_location, earliest_start_time,
    #                    latest_start_time, hard_constraints)
        task_performance = TaskPerformance.create(task)

        tasks_performance.append(task_performance)

    DatasetPerformance.create(dataset_id, tasks_performance)

    return tasks_performance


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
