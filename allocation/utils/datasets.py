import yaml
from allocation.config.task_factory import TaskFactory
import collections


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
        task = task_cls.from_dict(task_info)
        tasks.append(task)

    return tasks
