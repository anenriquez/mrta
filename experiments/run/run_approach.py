import argparse
import subprocess

from mrs.config.params import experiment_number, approach_number
from mrs.config.params import get_config_params


def start(robot_ids, docker_compose_file):
    subprocess.call(["docker-compose", "-f", docker_compose_file, "build", "mrta"])

    for robot_id in robot_ids:
        subprocess.call(["docker-compose", "-f", docker_compose_file, "up", "-d", "robot_proxy_"+ str(robot_id.split("_")[1])])
        subprocess.call(["docker-compose", "-f", docker_compose_file, "up", "-d", str(robot_id)])

    subprocess.call(["docker-compose", "-f", docker_compose_file, "up", "-d", "ccu"])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment', type=str, action='store', help='Experiment_name')
    parser.add_argument('approach', type=str, action='store', help='Approach name')
    parser.add_argument('n_runs', type=int, default=10)
    args = parser.parse_args()

    docker_compose_file_ = "docker_files/exp-" + experiment_number.get(args.experiment) + \
                           "-approach-" + approach_number.get(args.approach) + ".yaml"

    config_params = get_config_params(experiment=args.experiment)
    robot_ids_ = config_params.get("fleet")
    start(robot_ids_, docker_compose_file_)

    print("Running experiment {} approach {} {} times".format(args.experiment, args.approach, args.n_runs))

    for i in range(0, args.n_runs):
        subprocess.call(["docker-compose", "-f", docker_compose_file_, "up", "mrta"])
