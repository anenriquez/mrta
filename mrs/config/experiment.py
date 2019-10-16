from mrs.db.models.performance.experiment import Experiment
import logging


class ExperimentFactory:

    experiments = ['non_intentional_delays',
                   'intentional_delays',
                   'task_scalability',
                   'robot_scalability']

    def __init__(self, experiment_name, dataset_id, new_run=True):
        self.experiment_name = experiment_name
        self.dataset_id = dataset_id

        self.logger = logging.getLogger('mrs.experiment')
        if experiment_name not in self.experiments:
            self.logger.error("%s is not a valid experiment name", experiment_name)
            raise ValueError(experiment_name)

        self.experiment = Experiment.create(connection_alias=experiment_name,
                                            collection_name=dataset_id)

        if new_run:
            run_id = Experiment.get_new_run(self.experiment)
        else:
            run_id = Experiment.get_current_run(self.experiment)

        Experiment.set_run_id(self.experiment, run_id)

    def __call__(self, **kwargs):
        tasks = kwargs.get("tasks")
        if tasks:
            Experiment.add_performance_models(self.experiment, tasks, self.dataset_id)





