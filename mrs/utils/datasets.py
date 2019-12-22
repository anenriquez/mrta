import collections
from datetime import datetime, timedelta

import dateutil.parser
from fmlib.models.requests import TransportationRequest
from mrs.db.models.task import Task
from mrs.db.models.task import TimepointConstraint, TemporalConstraints
from mrs.utils.utils import load_yaml_file_from_module
from ropod.utils.uuid import generate_uuid


def load_tasks_to_db(dataset_module, dataset_name, **kwargs):
    dataset_dict = load_yaml_file_from_module(dataset_module, dataset_name + '.yaml')
    start_time = kwargs.get('start_time', datetime.now().isoformat())

    tasks_dict = dataset_dict.get('tasks')
    ordered_tasks = collections.OrderedDict(sorted(tasks_dict.items()))
    tasks = list()

    for task_id, task_info in ordered_tasks.items():
        earliest_pickup_time, latest_pickup_time = reference_to_start_time(task_info.get("earliest_pickup_time"),
                                                                           task_info.get("latest_pickup_time"),
                                                                           start_time)
        request = TransportationRequest(request_id=generate_uuid(),
                                        pickup_location=task_info.get('pickup_location'),
                                        delivery_location=task_info.get('delivery_location'),
                                        earliest_pickup_time=earliest_pickup_time,
                                        latest_pickup_time=latest_pickup_time,
                                        hard_constraints=task_info.get('hard_constraints'))

        pickup_constraint = TimepointConstraint(name="pickup",
                                                earliest_time=request.earliest_pickup_time,
                                                latest_time=request.latest_pickup_time)

        constraints = TemporalConstraints(timepoint_constraints=[pickup_constraint],
                                          hard=request.hard_constraints)

        task = Task.create_new(task_id=task_id, request=request, constraints=constraints)

        tasks.append(task)

    return tasks


def reference_to_start_time(earliest_time, latest_time, start_time_str=None):
    start_time = dateutil.parser.parse(start_time_str)

    r_earliest_time = start_time + timedelta(minutes=earliest_time)
    r_latest_time = start_time + timedelta(minutes=latest_time)

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
