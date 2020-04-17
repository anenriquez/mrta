from fmlib.config.params import ConfigParams as BaseConfigParams
from fmlib.utils.utils import load_file_from_module, load_yaml

experiment_number = {"non_intentional_delays": "1",
                     "intentional_delays": "2",
                     "task_scalability": "3",
                     "robot_scalability_1": "4-1",
                     "robot_scalability_2": "4-2",
                     "robot_scalability_3": "4-3",
                     "robot_scalability_4": "4-4",
                     "robot_scalability_5": "4-5",
                     }

approach_number = {"tessi-preventive-preempt": "1",
                   "tessi-preventive-re-allocate": "2",
                   "tessi-corrective-preempt": "3",
                   "tessi-corrective-re-allocate": "4",
                   "tessi-srea-preventive-preempt": "5",
                   "tessi-srea-preventive-re-allocate": "6",
                   "tessi-srea-preventive-re-schedule-preempt": "7",
                   "tessi-srea-preventive-re-schedule-re-allocate": "8",
                   "tessi-srea-corrective-preempt": "9",
                   "tessi-srea-corrective-re-allocate": "10",
                   "tessi-dsc-preventive-preempt": "11",
                   "tessi-dsc-preventive-re-allocate": "12",
                   "tessi-dsc-corrective-preempt": "13",
                   "tessi-dsc-corrective-re-allocate": "14",
                   }


class ConfigParams(BaseConfigParams):
    default_config_module = 'mrs.config.default'


def get_config_params(config_file=None, **kwargs):
    if config_file is None:
        config_params = ConfigParams.default()
    else:
        config_params = ConfigParams.from_file(config_file)

    experiment = kwargs.get("experiment")
    approach = kwargs.get("approach")

    if experiment is not None:
        experiments = load_file_from_module('experiments.config', 'config.yaml')
        experiment_config = {experiment: load_yaml(experiments).get(experiment)}
        config_params.update(**experiment_config.pop(experiment), experiment=experiment)

    if approach is not None:
        approaches = load_file_from_module('mrs.config.default', 'approaches.yaml')
        approach_config = {approach: load_yaml(approaches).get(approach)}
        config_params.update(**approach_config.pop(approach), approach=approach)

    return config_params
