import collections
from datetime import datetime, timedelta

from fmlib.models.requests import TransportationRequest
from fmlib.models.tasks import TransportationTask, TransportationTaskConstraints
from fmlib.models.tasks import TimepointConstraint, InterTimepointConstraint, TransportationTemporalConstraints
from ropod.utils.uuid import generate_uuid

from mrs.utils.utils import load_yaml_file_from_module


def load_tasks_to_db(dataset_module, dataset_name, **kwargs):
    dataset_dict = load_yaml_file_from_module(dataset_module, dataset_name + '.yaml')
    initial_time = kwargs.get('initial_time', datetime.now())

    tasks_dict = dataset_dict.get('tasks')
    ordered_tasks = collections.OrderedDict(sorted(tasks_dict.items()))
    tasks = list()

    for task_id, task_info in ordered_tasks.items():
        earliest_pickup_time, latest_pickup_time = reference_to_initial_time(task_info.get("earliest_pickup_time"),
                                                                             task_info.get("latest_pickup_time"),
                                                                             initial_time)
        request = TransportationRequest(request_id=generate_uuid(),
                                        pickup_location=task_info.get('pickup_location'),
                                        delivery_location=task_info.get('delivery_location'),
                                        earliest_pickup_time=earliest_pickup_time,
                                        latest_pickup_time=latest_pickup_time,
                                        hard_constraints=task_info.get('hard_constraints'))
        request.save()

        duration = InterTimepointConstraint()

        pickup = TimepointConstraint(earliest_time=request.earliest_pickup_time,
                                     latest_time=request.latest_pickup_time)

        temporal = TransportationTemporalConstraints(pickup=pickup, duration=duration)

        constraints = TransportationTaskConstraints(hard=request.hard_constraints, temporal=temporal)

        task = TransportationTask.create_new(task_id=task_id, request=request.request_id, constraints=constraints)

        tasks.append(task)

    return tasks


def reference_to_initial_time(earliest_time, latest_time, initial_time):
    r_earliest_time = initial_time + timedelta(seconds=earliest_time)
    r_latest_time = initial_time + timedelta(seconds=latest_time)
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
