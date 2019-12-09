import collections
from datetime import timedelta

import yaml
from fmlib.models.requests import TransportationRequest
from fmlib.models.tasks import TaskConstraints, TimepointConstraints
from fmlib.models.tasks import Task
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid


def load_yaml(file):
    """ Reads a yaml file and returns a dictionary with its contents

    :param file: file to load
    :return: data as dict()
    """
    with open(file, 'r') as file:
        data = yaml.safe_load(file)
    return data


def load_tasks_to_db(dataset_path):
    dataset_dict = load_yaml(dataset_path)

    tasks_dict = dataset_dict.get('tasks')
    ordered_tasks = collections.OrderedDict(sorted(tasks_dict.items()))
    tasks = list()

    for task_id, task_info in ordered_tasks.items():
        earliest_pickup_time, latest_pickup_time = reference_to_current_time(task_info.get("earliest_pickup_time"),
                                                                             task_info.get("latest_pickup_time"))
        request = TransportationRequest(request_id=generate_uuid(),
                                        pickup_location=task_info.get('pickup_location'),
                                        delivery_location=task_info.get('delivery_location'),
                                        earliest_pickup_time=earliest_pickup_time,
                                        latest_pickup_time=latest_pickup_time,
                                        hard_constraints=task_info.get('hard_constraints'))

        pickup_constraints = TimepointConstraints(earliest_time=request.earliest_pickup_time,
                                                  latest_time=request.latest_pickup_time)

        constraints = TaskConstraints(timepoint_constraints=[pickup_constraints],
                                      hard=request.hard_constraints)

        task = Task.create_new(task_id=task_id, request=request, constraints=constraints)

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
