import logging
import uuid

from mrs.db.models.performance.dataset import DatasetPerformance
from mrs.db.models.performance.task import TaskPerformance
from pymodm import fields, MongoModel
from pymodm.context_managers import switch_collection
from pymodm.context_managers import switch_connection
from pymodm.manager import Manager
from pymodm.queryset import QuerySet
from pymongo.errors import ServerSelectionTimeoutError


class ExperimentQuerySet(QuerySet):

    def get_task_performance(self, run_id, task_id):
        """return a task performance object matching to a task_id.
        """
        if isinstance(task_id, str):
            task_id = uuid.UUID(task_id)

        with switch_connection(Experiment, Experiment.Meta.connection_alias):
            with switch_collection(Experiment, Experiment.Meta.collection_name):
                run = self.get({'_id': run_id})
                for task_performance in run.tasks:
                    if task_performance.task.task_id == task_id:
                        return task_performance


ExperimentManager = Manager.from_queryset(ExperimentQuerySet)


class Experiment(MongoModel):
    run_id = fields.IntegerField(primary_key=True)
    tasks = fields.EmbeddedDocumentListField(TaskPerformance)
    dataset = fields.EmbeddedDocumentField(DatasetPerformance)
    objects = ExperimentManager()

    class Meta:
        ignore_unknown_fields = True

    @staticmethod
    def set_meta_info(connection_alias, collection_name):
        Experiment.Meta.connection_alias = connection_alias
        Experiment.Meta.collection_name = collection_name

    def save(self):
        try:
            with switch_connection(Experiment, Experiment.Meta.connection_alias):
                with switch_collection(Experiment, Experiment.Meta.collection_name):
                    super().save()

        except ServerSelectionTimeoutError:
            logging.warning('Could not save models to MongoDB')

    @classmethod
    def create(cls, connection_alias, collection_name):
        experiment = cls()
        experiment.set_meta_info(connection_alias, collection_name)
        return experiment

    @staticmethod
    def add_performance_models(experiment, tasks, dataset_id):
        task_models = Experiment.add_task_performance_models(experiment, tasks)
        Experiment.add_dataset_performance_model(experiment, task_models, dataset_id)

    @staticmethod
    def add_task_performance_models(experiment, tasks):
        task_models = list()
        for task in tasks:
            task_models.append(TaskPerformance.create(task=task,
                                                      connection_alias=experiment.Meta.connection_alias,
                                                      collection_name=experiment.Meta.collection_name))
        experiment.tasks = task_models
        experiment.save()
        return task_models

    @staticmethod
    def add_dataset_performance_model(experiment, task_models, dataset_id):
        dataset = DatasetPerformance(dataset_id=dataset_id, tasks=task_models)
        experiment.dataset = dataset
        experiment.save()
        return dataset

    @staticmethod
    def set_run_id(experiment, run_id):
        experiment.run_id = run_id
        experiment.save()

    @staticmethod
    def get_next_run_id(experiment, experiment_name, dataset_id):
        run_ids = list()

        if experiment.Meta.connection_alias == experiment_name and \
                experiment.Meta.collection_name == dataset_id:

            with switch_connection(experiment, experiment.Meta.connection_alias):
                with switch_collection(experiment, experiment.Meta.collection_name):
                    for run in Experiment.objects.all():
                        run_ids.append(run.run_id)

        if run_ids:
            previous_run = run_ids.pop()
            next_run = previous_run + 1
        else:
            next_run = 1

        return next_run

    @staticmethod
    def get_task_performance(run_id, task_id):
        return Experiment.objects.get_task_performance(run_id, task_id)

    def update_allocation(self, task_performance, allocation_time, robot_id, allocated=True):
        task_performance.allocation.allocated = allocated
        task_performance.allocation.allocation_time = allocation_time
        task_performance.allocation.robot_id = robot_id

        index = self.tasks.index(task_performance)
        print("index: ", index)
        self.tasks.pop(index)
        self.tasks.append(task_performance)

        print(task_performance.allocation.allocation_time)
        self.save()
