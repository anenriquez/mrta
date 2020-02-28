import argparse
import logging
import os
from datetime import datetime

import yaml
from fmlib.db.mongo import MongoStore
from experiments.db.models.experiment import Experiment as ExperimentModel
from fmlib.utils.utils import load_file_from_module, load_yaml
from mrs.utils.as_dict import AsDictMixin
from mrs.utils.utils import load_yaml_file_from_module
from ropod.structs.status import TaskStatus as TaskStatusConst


class PerformanceMetrics(AsDictMixin):
    def __init__(self, n_tasks, start_time, tasks_by_robot, n_allocated_tasks, n_re_allocation_attempts,
                 n_re_allocations, n_completed_tasks, n_aborted_tasks, n_delayed_tasks, allocation_time,
                 fleet_total_time, fleet_makespan, fleet_travel_time, fleet_work_time, fleet_idle_time,
                 fleet_robot_usage, robot_usage, most_loaded_robot, usage_most_loaded_robot):

        self.start_time = start_time
        self.tasks_by_robot = tasks_by_robot
        self.n_allocated_tasks = n_allocated_tasks
        self.n_re_allocation_attempts = n_re_allocation_attempts
        self.n_re_allocations = n_re_allocations
        self.n_completed_tasks = n_completed_tasks
        self.n_aborted_tasks = n_aborted_tasks
        self.n_delayed_tasks = n_delayed_tasks
        self.allocation_time = allocation_time
        self.fleet_total_time = fleet_total_time
        self.fleet_makespan = fleet_makespan
        self.fleet_travel_time = fleet_travel_time
        self.fleet_work_time = fleet_work_time
        self.fleet_idle_time = fleet_idle_time
        self.fleet_robot_usage = fleet_robot_usage
        self.robot_usage = robot_usage
        self.most_loaded_robot = most_loaded_robot
        self.usage_most_loaded_robot = usage_most_loaded_robot
        self.successful = (n_tasks == self.n_allocated_tasks == self.n_completed_tasks) and self.n_delayed_tasks == 0

    def __str__(self):
        to_print = ""
        dict_repr = self.to_dict()
        for key, value in dict_repr.items():
            to_print += key + ": " + str(value) + "\n"
        return to_print


class Run(AsDictMixin):
    def __init__(self, robot_ids, n_tasks, run_info):
        """ A run of an experiment

        run_id (int): Run number
        performance_metrics (PerformanceMetrics): Summarizes fleet performance
        robot_ids (list): ids of the robots in the fleet
        n_tasks (int): Number of tasks in the experiment
        run_info (ExperimentModel): Object that contains the data stored in the db for the run_id

        """
        self.run_id = run_info.run_id
        self.performance_metrics = None
        self._robot_ids = robot_ids
        self._n_tasks = n_tasks
        self._run_info = run_info

    def get_performance_metrics(self):
        start_time, finish_time = self.get_start_finish_time()
        tasks_by_robot = self.get_tasks_by_robot()
        allocated_tasks = self.get_allocated_tasks()
        n_allocated_tasks = len(allocated_tasks)
        n_re_allocation_attempts = self.get_n_re_allocation_attempts()
        n_re_allocations = self.get_n_re_allocations()
        n_completed_tasks = self.get_n_tasks_by_status(TaskStatusConst.COMPLETED)
        n_aborted_tasks = self.get_n_tasks_by_status(TaskStatusConst.ABORTED)
        n_delayed_tasks = self.get_n_delayed_tasks()
        allocation_time = self.get_allocation_time()
        fleet_total_time = (finish_time - start_time).total_seconds()
        fleet_travel_time = self.get_fleet_travel_time(fleet_total_time)
        fleet_work_time = self.get_fleet_work_time(fleet_total_time)
        fleet_idle_time = 100 - (fleet_travel_time + fleet_work_time)
        fleet_robot_usage = self.get_fleet_robot_usage()
        robot_usage = self.get_robot_usage(n_allocated_tasks, tasks_by_robot)
        usage, robot_id = self.get_most_loaded_robot(robot_usage)

        metrics = {"n_tasks": self._n_tasks,
                   "start_time": start_time.isoformat(),
                   "tasks_by_robot": tasks_by_robot,
                   "n_allocated_tasks": n_allocated_tasks,
                   "n_re_allocation_attempts": n_re_allocation_attempts,
                   "n_re_allocations": n_re_allocations,
                   "n_completed_tasks": n_completed_tasks,
                   "n_aborted_tasks": n_aborted_tasks,
                   "n_delayed_tasks": n_delayed_tasks,
                   "allocation_time": allocation_time,
                   "fleet_total_time": fleet_total_time,
                   "fleet_makespan": finish_time.isoformat(),
                   "fleet_travel_time": fleet_travel_time,
                   "fleet_work_time": fleet_work_time,
                   "fleet_idle_time": fleet_idle_time,
                   "fleet_robot_usage": fleet_robot_usage,
                   "robot_usage": robot_usage,
                   "most_loaded_robot": robot_id,
                   "usage_most_loaded_robot": usage}

        self.performance_metrics = PerformanceMetrics(**metrics)

    def get_allocated_tasks(self):
        allocated_tasks = list()
        for performance in self._run_info.tasks_performance:
            if performance.allocation and performance.allocation.allocated:
                allocated_tasks.append(performance.task_id)
        return allocated_tasks

    def get_n_re_allocation_attempts(self):
        n_re_allocation_attempts = 0
        for performance in self._run_info.tasks_performance:
            n_re_allocation_attempts += performance.allocation.n_re_allocation_attempts
        return n_re_allocation_attempts

    def get_n_re_allocations(self):
        n_re_allocations = 0
        for performance in self._run_info.tasks_performance:
            n_re_allocations += (len(performance.allocation.time_to_allocate)-1)
        return n_re_allocations

    def get_n_tasks_by_status(self, status):
        n_tasks = 0
        for task_status in self._run_info.tasks_status:
            if task_status.status == status:
                n_tasks += 1
        return n_tasks

    def get_n_delayed_tasks(self):
        n_delayed_tasks = 0
        for task_status in self._run_info.tasks_status:
            if task_status.delayed:
                n_delayed_tasks += 1
        return n_delayed_tasks

    def get_allocation_time(self):
        allocation_time = 0
        for performance in self._run_info.tasks_performance:
            for time_ in performance.allocation.time_to_allocate:
                allocation_time += time_
        return allocation_time

    def get_fleet_travel_time(self, fleet_total_time):
        travel_time = 0
        for performance in self._run_info.robots_performance:
            travel_time += performance.travel_time
        return 100 * travel_time/(fleet_total_time*len(self._robot_ids))

    def get_fleet_work_time(self, fleet_total_time):
        work_time = 0
        for performance in self._run_info.robots_performance:
            work_time += performance.work_time
        return 100 * work_time/(fleet_total_time*len(self._robot_ids))

    def get_fleet_robot_usage(self):
        n_robots_used = 0
        for performance in self._run_info.robots_performance:
            if performance.total_time > 0.0:
                n_robots_used += 1
        return (n_robots_used/len(self._robot_ids)) * 100

    def get_tasks_by_robot(self):
        tasks_by_robot = {robot_id: list() for robot_id in self._robot_ids}
        for task in self._run_info.tasks:
            for robot_id in task.assigned_robots:
                tasks_by_robot[robot_id].append(str(task.task_id))
        return tasks_by_robot

    def get_robot_usage(self, n_allocated_tasks, tasks_by_robot):
        robot_usage = {robot_id: 0.0 for robot_id in self._robot_ids}
        for robot_id, tasks in tasks_by_robot.items():
            robot_usage[robot_id] = 100 * (len(tasks)/n_allocated_tasks)
        return robot_usage

    @staticmethod
    def get_most_loaded_robot(robot_usage):
        return max(zip(robot_usage.values(), robot_usage.keys()))

    def get_start_finish_time(self):
        start_time = datetime.max
        finish_time = datetime.min
        task_status = [task_status for task_status in self._run_info.tasks_status
                       if task_status.status == TaskStatusConst.COMPLETED]
        for task_status in task_status:
            for action_progress in task_status.progress.actions:
                if action_progress.start_time < start_time:
                    start_time = action_progress.start_time
                if action_progress.finish_time > finish_time:
                    finish_time = action_progress.finish_time
        return start_time, finish_time


class Experiment(AsDictMixin):
    def __init__(self, name, approach, robot_ids, dataset_name, n_tasks):
        """ An experiment

        name (str): Name of the experiment
        approach (str): Name of the approach
        robot_ids (list): ids of the robots in the fleet
        dataset_name (str): Name of the dataset
        n_tasks (int): Number of tasks in the experiment
        runs (list): List of Runs
        success_rate (float): from 0.0 to 1.0
                            successful_runs/n_runs
                            a run is successful if all tasks are allocated and completed
                            on time
        """
        self.name = name
        self.approach = approach
        self.robot_ids = robot_ids
        self.dataset_name = dataset_name
        self.n_tasks = n_tasks
        self.runs = list()
        self.success_rate = 0.0

    def to_dict(self):
        dict_repr = super().to_dict()
        runs_dict = dict()
        for run in self.runs:
            runs_dict[run.run_id] = run.to_dict()
        dict_repr.update(runs=runs_dict)
        return dict_repr

    def to_file(self, file_path):
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_ = file_path + self.dataset_name + ".yaml"

        with open(file_, 'w') as outfile:
            data = self.to_dict()
            yaml.safe_dump(data, outfile, default_flow_style=False)

    def get_runs_info_from_db(self):
        MongoStore(db_name=self.name)
        return ExperimentModel.get_experiments(self.approach, self.dataset_name)

    def get_success_rate(self):
        return len([run for run in self.runs if run.performance_metrics.successful]) / len(self.runs)

    def get_results(self):
        runs_info = self.get_runs_info_from_db()
        for run_info in runs_info:
            run = Run(robot_ids, self.n_tasks, run_info)
            run.get_performance_metrics()
            print("Run {}: {} ".format(run.run_id, "successful" if run.performance_metrics.successful
                                                                    else "unsuccessful"))
            self.runs.append(run)
        self.success_rate = self.get_success_rate()


def get_experiment(name, approach, robot_ids, dataset_module, dataset_name):
    dataset_dict = load_yaml_file_from_module(dataset_module, dataset_name + '.yaml')
    n_tasks = len(dataset_dict.get("tasks"))
    experiment = Experiment(name, approach, robot_ids, dataset_name, n_tasks)
    experiment.get_results()
    return experiment


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment_name', type=str, action='store', help='Experiment_name')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--approach', type=str, action='store', default='tessi-corrective-abort', help='Approach name')
    group.add_argument('--all', action='store_true')
    args = parser.parse_args()

    experiments = load_file_from_module('experiments.config', 'config.yaml')
    experiment_config = {args.experiment_name: load_yaml(experiments).get(args.experiment_name)}.pop(args.experiment_name)

    robot_ids = experiment_config.get("fleet")
    dataset_module = experiment_config.get("dataset_module")
    datasets = experiment_config.get("datasets")
    experiments = list()

    logging.basicConfig(level=logging.DEBUG)

    logging.info("Getting results for experiment: %s", args.experiment_name)

    if args.all:
        approaches = experiment_config.get("approaches")
        for approach in approaches:
            logging.info("Approach: %s", approach)
            for dataset_name in datasets:
                experiment = get_experiment(args.experiment_name, approach, robot_ids, dataset_module, dataset_name)
                experiments.append(experiment)
    else:
        logging.info("Approach: %s", args.approach)
        for dataset_name in datasets:
            experiment = get_experiment(args.experiment_name, args.approach, robot_ids, dataset_module, dataset_name)
            experiments.append(experiment)

    for experiment in experiments:
        file_path = experiment.name + "/" + experiment.approach + "/"
        experiment.to_file(file_path)
