import argparse

from fmlib.utils.utils import load_file_from_module, load_yaml
from mrs.config.params import approach_number, ConfigParams
from mrs.utils.docker import TestComposeFileGenerator


def generate_docker_compose_file(n_robots, approach):
    file_generator = TestComposeFileGenerator(n_robots, {"approach": approach}, test_kwargs={"approach": approach})
    file_path = "./"
    file_name = "approach-" + approach_number.get(approach)
    file_generator.generate_docker_compose_file(file_path, file_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    group.add_argument('--approach', type=str, action='store', help='Experiment_name')
    group.add_argument('--all', action='store_true')
    args = parser.parse_args()

    if args.file is None:
        config_params = ConfigParams.default()
    else:
        config_params = ConfigParams.from_file(args.file)

    approaches = load_file_from_module('mrs.config.default', 'approaches.yaml')
    approaches_config = load_yaml(approaches)
    n_robots_ = len(config_params.get("fleet"))

    if args.all:
        print(approaches_config)
        for approach_ in approaches_config.keys():
            generate_docker_compose_file(n_robots_, approach_)
    else:
        generate_docker_compose_file(n_robots_, args.approach)
