from fmlib.config.params import ConfigParams as BaseConfigParams
from fmlib.utils.utils import load_file_from_module, load_yaml


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
