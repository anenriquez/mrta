import copy
import os

import yaml


class ComposeFileGenerator:
    def __init__(self, n_robots, component_kwargs):
        self.n_robots = n_robots
        self.component_kwargs = component_kwargs
        self.robot_ids = self.generate_robot_ids()

        self.mongo_service = {"container_name": "mongo",
                              "image": "mongo:4.0-xenial",
                              "volumes": ["/data/db:/data/db"],
                              "ports": ["27017:27017"],
                              "network_mode": "host",
                              }

        self.component_template = {"image": "ropod-mrs",
                                   "working_dir": "/mrta/mrs/",
                                   "network_mode": "host",
                                   "tty": "true",
                                   "stdin_open": "true",
                                   "depends_on": ["mongo"],
                                   }

    def generate_robot_ids(self):
        robot_ids = list()
        for i in range(1, self.n_robots+1):
            robot_ids.append("robot_" + "{:03d}".format(i))
        return robot_ids

    def generate_ccu_service(self):
        ccu_service = dict()
        command = ["python3", "ccu.py"]
        for arg_name, value in self.component_kwargs.items():
            command.append("--" + arg_name)
            command.append(value)

        ccu_service["ccu"] = copy.deepcopy(self.component_template)
        ccu_service["ccu"].update(container_name="ccu",
                                  command=command)
        return ccu_service

    def generate_mongo_service(self):
        mongo_service = dict()
        mongo_service["mongo"] = copy.deepcopy(self.mongo_service)
        return mongo_service

    def generate_robot_services(self):
        robot_services = dict()
        for robot_id in self.robot_ids:
            robot_service = self.generate_robot_service(robot_id)
            robot_services[robot_id] = robot_service
        return robot_services

    def generate_robot_proxy_services(self):
        robot_proxy_services = dict()
        for robot_id in self.robot_ids:
            robot_proxy_service = self.generate_robot_proxy_service(robot_id)
            robot_proxy_services["robot_proxy_" + robot_id.split('_')[1]] = robot_proxy_service
        return robot_proxy_services

    def generate_robot_service(self, robot_id):
        command = ["python3", "robot.py", robot_id]
        for arg_name, value in self.component_kwargs.items():
            command.append("--" + arg_name)
            command.append(value)

        robot_service = copy.deepcopy(self.component_template)
        robot_service.update(container_name=robot_id,
                             command=command)
        return robot_service

    def generate_robot_proxy_service(self, robot_id):
        command = ["python3", "robot_proxy.py", robot_id]
        for arg_name, value in self.component_kwargs.items():
            command.append("--" + arg_name)
            command.append(value)

        robot_service = copy.deepcopy(self.component_template)
        robot_service.update(container_name="robot_proxy_" + robot_id.split('_')[1],
                             command=command)
        return robot_service

    def generate_services(self):
        services = dict()
        services["version"] = "2"
        services["services"] = dict()

        robot_services = self.generate_robot_services()
        robot_proxy_services = self.generate_robot_proxy_services()
        ccu_service = self.generate_ccu_service()
        mongo_service = self.generate_mongo_service()

        services = self.add_services(services, ccu_service)
        services = self.add_services(services, mongo_service)
        services = self.add_services(services, robot_services)
        services = self.add_services(services, robot_proxy_services)

        return services

    def generate_docker_compose_file(self, file_path, file_name):
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_ = file_path + file_name + ".yaml"
        services = self.generate_services()

        with open(file_, 'w') as outfile:
            yaml.safe_dump(services, outfile, default_flow_style=False)

    @staticmethod
    def add_services(services, new_services):
        for key, value in new_services.items():
            services["services"][key] = value
        return services


class TestComposeFileGenerator(ComposeFileGenerator):
    def __init__(self, n_robots, component_kwargs, **kwargs):
        super().__init__(n_robots, component_kwargs)
        self.test_kwargs = kwargs.get("test_kwargs")

        self.test_service = {"build": {"context": "../../..",
                                       "dockerfile": "Dockerfile"},
                             "container_name": "mrta",
                             "working_dir": "/mrta/mrs/tests/",
                             }

    def generate_test_service(self):
        test_service = dict()
        command = ["python3", "test.py"]
        for arg_name, value in self.test_kwargs.items():
            command.append("--" + arg_name)
            command.append(value)

        test_service["mrta"] = copy.deepcopy(self.component_template)
        test_service["mrta"].pop("depends_on")
        test_service["mrta"].update(command=command, **self.test_service)
        return test_service

    def generate_services(self):
        services = super().generate_services()
        test_service = self.generate_test_service()
        services = self.add_services(services, test_service)
        return services


class ExperimentComposeFileGenerator(ComposeFileGenerator):
    def __init__(self, n_robots, component_kwargs, experiment_args):
        super().__init__(n_robots, component_kwargs)
        self.experiment_args = experiment_args

        self.experiment_service = {"build": {"context": "../../",
                                             "dockerfile": "Dockerfile"},
                                   "container_name": "mrta",
                                   "working_dir": "/mrta/experiments/",
                                   }

    def generate_experiment_service(self):
        experiment_service = dict()
        command = ["python3", "experiment.py"]
        for arg in self.experiment_args:
            command.append(arg)

        experiment_service["mrta"] = copy.deepcopy(self.component_template)
        experiment_service["mrta"].pop("depends_on")
        experiment_service["mrta"].update(command=command, **self.experiment_service)
        return experiment_service

    def generate_services(self):
        services = super().generate_services()
        experiment_service = self.generate_experiment_service()
        services = self.add_services(services, experiment_service)
        return services
