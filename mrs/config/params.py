from fmlib.config.params import ConfigParams as BaseConfigParams
from fmlib.utils.utils import load_file_from_module, load_yaml

experiment_number = {"non_intentional_delays": "1",
                     "intentional_delays": "2",
                     "task_scalability": "3",
                     "robot_scalability_10": "4-10",
                     "robot_scalability_20": "4-20",
                     "robot_scalability_30": "4-30",
                     "robot_scalability_40": "4-40",
                     "robot_scalability_50": "4-50",
                     }

approach_number = {"tessi-preventive-abort": "1",
                   "tessi-preventive-re-allocate": "2",
                   "tessi-corrective-abort": "3",
                   "tessi-corrective-re-allocate": "4",
                   "tessi-srea-preventive-abort": "5",
                   "tessi-srea-preventive-re-allocate": "6",
                   "tessi-srea-preventive-re-schedule-abort": "7",
                   "tessi-srea-preventive-re-schedule-re-allocate": "8",
                   "tessi-srea-corrective-abort": "9",
                   "tessi-srea-corrective-re-allocate": "10",
                   "tessi-dsc-preventive-abort": "11",
                   "tessi-dsc-preventive-re-allocate": "12",
                   "tessi-dsc-corrective-abort": "13",
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
        experiments = load_file_from_module('mrs.experiments.config', 'config.yaml')
        experiment_config = {experiment: load_yaml(experiments).get(experiment)}
        config_params.update(**experiment_config.pop(experiment), experiment=experiment)

    if approach is not None:
        approaches = load_file_from_module('mrs.config.default', 'approaches.yaml')
        approach_config = {approach: load_yaml(approaches).get(approach)}
        config_params.update(**approach_config.pop(approach), approach=approach)

    return config_params
