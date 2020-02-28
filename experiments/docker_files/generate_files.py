import argparse

from fmlib.utils.utils import load_file_from_module, load_yaml
from mrs.config.params import experiment_number, approach_number
from mrs.utils.docker import ExperimentComposeFileGenerator


def generate_docker_compose_files(experiment_name, experiment_config):
    n_robots = len(experiment_config.get("fleet"))
    for approach in experiment_config.get("approaches"):
        component_kwargs = {"experiment": experiment_name, "approach": approach}
        experiment_args = [experiment_name, approach]
        generate_docker_compose_file(n_robots, component_kwargs, experiment_args)


def generate_docker_compose_file(n_robots, component_kwargs, experiment_args):
    file_generator = ExperimentComposeFileGenerator(n_robots, component_kwargs, experiment_args)
    file_path = "./"
    experiment_name = component_kwargs.get("experiment")
    approach = component_kwargs.get("approach")
    file_name = "exp-" + experiment_number.get(experiment_name) + "-approach-" + approach_number.get(approach)
    file_generator.generate_docker_compose_file(file_path, file_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--experiment_name', type=str, action='store', help='Experiment_name')
    group.add_argument('--all', action='store_true')
    args = parser.parse_args()

    experiments = load_file_from_module('experiments.config', 'config.yaml')
    experiments_config = load_yaml(experiments)

    if args.all:
        for experiment_name_, config in experiments_config.items():
            generate_docker_compose_files(experiment_name_, config)
    else:
        config = experiments_config.get(args.experiment_name)
        generate_docker_compose_files(args.experiment_name, config)
