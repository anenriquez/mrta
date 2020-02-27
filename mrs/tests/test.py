import argparse
from mrs.config.params import get_config_params
from mrs.allocate import Allocate
from mrs.utils.utils import load_yaml_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('--approach', type=str, action='store', help='Approach name')
    parser.add_argument('--robot_poses_file', type=str, action='store',
                        default='../config/default/robot_init_poses.yaml', help='Path to robot init poses file')
    parser.add_argument('--dataset_module', type=str, action='store', help='Dataset module',
                        default='mrs.tests.datasets')
    parser.add_argument('--dataset_name', type=str, action='store', help='Dataset name',
                        default='non_overlapping')
    args = parser.parse_args()

    robot_poses = load_yaml_file(args.robot_poses_file)

    config_params = get_config_params(args.file, approach=args.approach)
    print("Testing approach: ", config_params.get("approach"))

    allocate = Allocate(config_params, robot_poses, args.dataset_module, args.dataset_name)
    allocate.run()
