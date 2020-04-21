import argparse
import logging
import os
import uuid
from datetime import datetime

import numpy as np
import yaml
from fmlib.db.mongo import MongoStore
from ropod.structs.status import TaskStatus as TaskStatusConst

from experiments.db.models.experiment import Experiment as ExperimentModel
from experiments.results.plot.gantt import get_gantt_tasks_schedule, get_gantt_robots_d_graphs, get_gif
from mrs.config.params import get_config_params
from mrs.utils.as_dict import AsDictMixin
from mrs.utils.utils import load_yaml_file_from_module
from ropod.utils.uuid import from_str


class TimeDistribution(AsDictMixin):
    def __init__(self, total_time, travel_time, work_time, idle_time):
        self.total_time = total_time
        self.travel_time = travel_time
        self.work_time = work_time
        self.idle_time = idle_time


class ExecutionTimes(AsDictMixin):
    def __init__(self, start_time, pickup_time, delivery_time):
        self.start_time = start_time
        self.pickup_time = pickup_time
        self.delivery_time = delivery_time


class TaskPerformanceMetrics(AsDictMixin):
    def __init__(self, task_id, status, delay=0, earliness=0, **kwargs):
        if isinstance(task_id, uuid.UUID):
            task_id = str(task_id)
        self.task_id = task_id
        self.status = status
        self.delay = delay
        self.earliness = earliness
        self.execution_times = kwargs.get("execution_times")
        self.allocation_time = 0  # Time to allocate the task the first time
        self.re_allocation_time = 0
        self.n_re_allocation_attempts = 0
        self.n_re_allocations = 0

    def get_metrics(self, task_performance):
        if task_performance.allocation:
            allocation_times = task_performance.allocation.time_to_allocate
            self.allocation_time = allocation_times[0]
            self.re_allocation_time = sum(allocation_times[1:])
            self.n_re_allocation_attempts = task_performance.allocation.n_re_allocation_attempts
            self.n_re_allocations = len(allocation_times) - 1


class RobotPerformanceMetrics(AsDictMixin):
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.robot_tasks = list()
        self.time_distribution = None
        self.usage = 0
        self.dgraph_recomputation_time = 0

    def __str__(self):
        return str(self.to_dict())

    def get_metrics(self, run_info, completed_tasks, total_n_tasks):
        # robot_peformance.allocated_tasks include all tasks allocated to the robot, but some of these could have been
        # re-allocated. Take robots from task.assigned_robots
        print("robot: ", self.robot_id)
        for task_id in completed_tasks:
            task = FleetPerformanceMetrics.get_task(run_info, task_id)
            if self.robot_id in task.assigned_robots:
                self.robot_tasks.append(task_id)
        print("robot tasks: ", self.robot_tasks)
        self.time_distribution = self.get_time_distribution(run_info)
        self.usage = 100 * (len(self.robot_tasks)/total_n_tasks)
        robot_performance = self.get_robot_performance(run_info, self.robot_id)
        self.dgraph_recomputation_time = sum(robot_performance.dgraph_recomputation_time)

    def get_time_distribution(self, run_info):
        travel_time = 0
        work_time = 0
        idle_time = 0
        # Robot tasks include completed tasks (have execution information) only
        tasks_performance = list()
        for task_id in self.robot_tasks:
            performance = FleetPerformanceMetrics.get_task_performance(run_info, from_str(task_id))
            tasks_performance.append(performance)

        # Order from earliest to latest
        tasks_performance = sorted(tasks_performance, key=lambda p: p.execution.start_time)

        for i, performance in enumerate(tasks_performance):
            travel_time += (performance.execution.pickup_time - performance.execution.start_time).total_seconds()
            work_time += (performance.execution.delivery_time - performance.execution.pickup_time).total_seconds()

            if i > 0:
                previous_performance = tasks_performance[i-1]
                idle_time += (performance.execution.start_time - previous_performance.execution.delivery_time).total_seconds()

        start_time = tasks_performance[0].execution.start_time
        finish_time = tasks_performance[-1].execution.delivery_time
        total_time = (finish_time - start_time).total_seconds()

        return TimeDistribution(total_time, travel_time, work_time, idle_time)

    @staticmethod
    def get_robot_performance(run_info, robot_id):
        for performance in run_info.robots_performance:
            if performance.robot_id == robot_id:
                return performance


class FleetPerformanceMetrics(AsDictMixin):
    def __init__(self, robot_ids):
        self._robot_ids = robot_ids
        self.robots_performance_metrics = None
        self.tasks_performance_metrics = None

        self.total_n_tasks = 0
        self.allocated_tasks = list()
        self.unallocated_tasks = list()
        self.unsuccessful_reallocations = list()
        self.successful_reallocations = list()
        self.completed_tasks = list()
        self.preempted_tasks = list()
        self.delayed_tasks = list()
        self.early_tasks = list()
        self.successful_tasks = list()

        self.delay = 0
        self.earliness = 0
        self.time_distribution = None
        self.usage = None
        self.biggest_load = None

    def to_dict(self):
        dict_repr = super().to_dict()
        robots_performance_metrics = list()
        tasks_performance_metrics = list()

        for robot in self.robots_performance_metrics:
            robots_performance_metrics.append(robot.to_dict())
        dict_repr.update(robots_performance_metrics=robots_performance_metrics)

        for task in self.tasks_performance_metrics:
            tasks_performance_metrics.append(task.to_dict())
        dict_repr.update(tasks_performance_metrics=tasks_performance_metrics)
        return dict_repr

    def get_metrics(self, run_info):
        self.total_n_tasks = len(run_info.tasks)
        self.allocated_tasks = self.get_allocated_tasks(run_info)
        self.unallocated_tasks = self.get_unallocated_tasks(run_info)
        self.unsuccessful_reallocations = self.get_unsuccessful_reallocations(run_info)
        self.successful_reallocations = self.get_successful_reallocations(run_info)
        self.completed_tasks = self.get_tasks_by_status(run_info, TaskStatusConst.COMPLETED)
        self.preempted_tasks = self.get_preempted_tasks(run_info)
        self.tasks_performance_metrics = self.get_tasks_performance_metrics(run_info)

        self.successful_tasks = [task for task in self.completed_tasks if task not in self.delayed_tasks
                                 and task not in self.early_tasks]

        self.robots_performance_metrics = self.get_robots_performance_metrics(run_info, self.completed_tasks, self.total_n_tasks)
        self.usage = self.get_fleet_usage(run_info)
        self.biggest_load = self.get_biggest_load()

    @staticmethod
    def get_allocated_tasks(run_info):
        # Tasks that were allocated at least once, regardless if they were preempted or re-allocated after their
        # first allocation
        allocated_tasks = list()
        for task_performance in run_info.tasks_performance:
            if task_performance.allocation:
                allocated_tasks.append(str(task_performance.task_id))
        return allocated_tasks

    @staticmethod
    def get_unallocated_tasks(run_info):
        # Tasks that were never allocated
        unallocated_tasks = list()
        for task_performance in run_info.tasks_performance:
            if not task_performance.allocation:
                unallocated_tasks.append(str(task_performance.task_id))
        return unallocated_tasks

    @staticmethod
    def get_unsuccessful_reallocations(run_info):
        # Tasks that entered a re-allocation process and could not be re-allocated
        unsuccessful_reallocations = list()
        for task_performance in run_info.tasks_performance:
            if task_performance.allocation and \
                    task_performance.allocation.n_re_allocation_attempts > 0 \
                    and not task_performance.allocation.allocated:
                unsuccessful_reallocations.append(str(task_performance.task_id))
        return unsuccessful_reallocations

    @staticmethod
    def get_successful_reallocations(run_info):
        # Tasks that entered a re-allocation process and could be re-allocated
        successful_reallocations = list()
        for task_performance in run_info.tasks_performance:
            if task_performance.allocation and \
                    task_performance.allocation.n_re_allocation_attempts > 0 \
                    and task_performance.allocation.allocated:
                successful_reallocations.append(str(task_performance.task_id))
        return successful_reallocations

    @staticmethod
    def get_preempted_tasks(run_info):
        # Preempted tasks were allocated but then preempted (recovery mechanism)
        preempted_tasks = list()
        for task_performance in run_info.tasks_performance:
            if task_performance.allocation and not \
                    task_performance.execution and \
                    task_performance.allocation.n_re_allocation_attempts == 0:
                preempted_tasks.append(str(task_performance.task_id))

        return preempted_tasks

    def get_tasks_performance_metrics(self, run_info):
        tasks_performance_metrics = list()
        for task in run_info.tasks:
            task_status = self.get_task_status(run_info, task)
            task_performance = [p for p in run_info.tasks_performance if p.task_id == task.task_id].pop()

            if task_performance.execution:
                d = self.get_delay(task, task_performance)
                if d > 0:
                    self.delayed_tasks.append(str(task.task_id))
                    self.delay += d
                e = self.get_earliness(task, task_performance)
                if e > 0:
                    self.early_tasks.append(str(task.task_id))
                    self.earliness += e

                execution_times = ExecutionTimes(task_performance.execution.start_time,
                                                 task_performance.execution.pickup_time,
                                                 task_performance.execution.delivery_time)

                task_performance_metrics = TaskPerformanceMetrics(task.task_id, task_status.status, d, e,
                                                                  execution_times=execution_times)
            else:
                task_performance_metrics = TaskPerformanceMetrics(task.task_id, task_status.status)

            task_performance_metrics.get_metrics(task_performance)
            tasks_performance_metrics.append(task_performance_metrics)

        return tasks_performance_metrics

    def get_robots_performance_metrics(self, run_info, completed_tasks, total_n_tasks):
        robots_performance_metrics = list()
        for robot_id in self._robot_ids:
            robot_performance_metrics = RobotPerformanceMetrics(robot_id)
            robot_performance_metrics.get_metrics(run_info, completed_tasks, total_n_tasks)
            robots_performance_metrics.append(robot_performance_metrics)
        return robots_performance_metrics

    # def get_time_distribution(self, start_time, finish_time):
    #     # TODO: Use the same finish time and start time for all methods and all runs
    #     # total_time = (finish_time - start_time).total_seconds()
    #     travel_time = 0
    #     work_time = 0
    #
    #     for robot in self.robots_performance_metrics:
    #         if robot.time_distribution:
    #             travel_time += robot.time_distribution.travel_time
    #             work_time += robot.time_distribution.work_time
    #
    #     # fleet_travel_time = 100 * travel_time / (total_time * len(self._robot_ids))
    #     # fleet_work_time = 100 * work_time / (total_time * len(self._robot_ids))
    #     # fleet_idle_time = 100 - (fleet_travel_time + fleet_work_time)
    #
    #     return TimeDistribution(total_time, fleet_travel_time, fleet_work_time, fleet_idle_time)

    def get_fleet_usage(self, run_info):
        n_robots_used = 0
        for performance in run_info.robots_performance:
            if performance.total_time > 0.0:
                n_robots_used += 1
        return (n_robots_used/len(self._robot_ids)) * 100

    def get_biggest_load(self):
        biggest_load = - np.inf
        for robot in self.robots_performance_metrics:
            if robot.usage > biggest_load:
                biggest_load = robot.usage
        return biggest_load

    @staticmethod
    def get_tasks_by_status(run_info, status):
        task_ids = list()
        for task_status in run_info.tasks_status:
            if task_status.status == status:
                dict_repr = task_status.to_son().to_dict()
                task_id = str(dict_repr.get('_id'))
                task_ids.append(task_id)
        return task_ids

    @staticmethod
    def get_task(run_info, task_id):
        if isinstance(task_id, str):
            task_id = uuid.UUID(task_id)
        for task in run_info.tasks:
            if task.task_id == task_id:
                return task

    @staticmethod
    def get_task_status(run_info, task):
        for task_status in run_info.tasks_status:
            dict_repr = task_status.to_son().to_dict()
            task_id = dict_repr.get('_id')
            if task.task_id == task_id:
                return task_status

    @staticmethod
    def get_task_performance(run_info, task_id):
        for performance in run_info.tasks_performance:
            if performance.task_id == task_id:
                return performance

    @staticmethod
    def get_delay(task, task_performance):
        # Tasks are marked as delayed if they were executed later than their allotted timeslot in the dispatchable graph
        # However, for the experiments only tasks that did not complaint with the pickup temporal constraint are marked
        # as delayed
        latest_pickup_time = task.constraints.temporal.pickup.latest_time

        if task_performance.execution.pickup_time > latest_pickup_time:
            delay = (task_performance.execution.pickup_time - latest_pickup_time).seconds
        else:
            delay = 0
        return delay

    @staticmethod
    def get_earliness(task, task_performance):
        # Tasks are marked as early if they were executed earlier than their allotted timeslot in the dispatchable graph
        # However, for the experiments only tasks that did not complaint with the pickup temporal constraint are marked
        # as early
        earliest_pickup_time = task.constraints.temporal.pickup.earliest_time

        if task_performance.execution.pickup_time < earliest_pickup_time:
            earliness = (earliest_pickup_time - task_performance.execution.pickup_time).seconds
        else:
            earliness = 0
        return earliness


class PerformanceMetrics(AsDictMixin):
    def __init__(self, n_tasks, start_time, finish_time, fleet_performance_metrics):
        self.start_time = start_time
        self.finish_time = finish_time
        self.fleet_performance_metrics = fleet_performance_metrics
        self.n_successful_tasks = len(self.fleet_performance_metrics.successful_tasks)
        # % of completed tasks on time
        self.successful_percentage = 100 * self.n_successful_tasks/self.fleet_performance_metrics.total_n_tasks

    def to_dict(self):
        dict_repr = super().to_dict()
        dict_repr.update(fleet_performance_metrics=self.fleet_performance_metrics.to_dict())
        return dict_repr


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

    def to_dict(self):
        dict_repr = super().to_dict()
        dict_repr.update(performance_metrics=self.performance_metrics.to_dict())
        return dict_repr

    def get_performance_metrics(self):
        start_time, finish_time = self.get_start_finish_time()
        fleet_performance_metrics = FleetPerformanceMetrics(self._robot_ids)
        fleet_performance_metrics.get_metrics(self._run_info)
        self.performance_metrics = PerformanceMetrics(self._n_tasks, start_time, finish_time, fleet_performance_metrics)

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
    def __init__(self, name, approach, bidding_rule, robot_ids, dataset_name, n_tasks):
        """ An experiment

        name (str): Name of the experiment
        approach (str): Name of the approach
        bidding_rule (str): Name of the bidding rule
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
        self.bidding_rule = bidding_rule
        self._robot_ids = robot_ids
        self.dataset_name = dataset_name
        self.n_tasks = n_tasks
        self.runs = list()
        self.avg_successful_tasks = 0.0
        self.avg_successful_percentage = 0.0

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
        return ExperimentModel.get_experiments(self.approach, bidding_rule, self.dataset_name)

    def get_avg_success(self):
        n_successful_tasks = [run.performance_metrics.n_successful_tasks for run in self.runs]
        self.avg_successful_tasks = sum(n_successful_tasks)/len(n_successful_tasks)
        self.avg_successful_percentage = 100 * self.avg_successful_tasks / self.n_tasks

    def get_results(self):
        runs_info = self.get_runs_info_from_db()
        logging.info("Number of runs: %s", len(runs_info))

        for run_info in runs_info:
            run = Run(self._robot_ids, self.n_tasks, run_info)
            run.get_performance_metrics()
            self.runs.append(run)
        #self.get_avg_success()
        # self.success_rate = self.get_success_rate()


def get_experiment(name, approach, bidding_rule, robot_ids, dataset_module, dataset_name):
    logging.info("Approach: %s", approach)
    logging.info("Bidding rule: %s", bidding_rule)
    logging.info("Dataset: %s", dataset_name)

    dataset_dict = load_yaml_file_from_module(dataset_module, dataset_name + '.yaml')
    n_tasks = len(dataset_dict.get("tasks"))
    experiment = Experiment(name, approach, bidding_rule, robot_ids, dataset_name, n_tasks)
    experiment.get_results()
    return experiment


def plot_task_schedules(experiment, file_path):
    runs_info = experiment.get_runs_info_from_db()
    for run_info in runs_info:
        get_gantt_tasks_schedule('task_schedules', run_info.tasks,
                                 run_info.tasks_performance,
                                 dir=file_path + '/run_ ' + str(run_info.run_id))


def plot_robots_d_graphs(experiment, file_path):
    runs_info = experiment.get_runs_info_from_db()
    for run_info in runs_info:
        for robot_performance in run_info.robots_performance:
            if robot_performance.allocated_tasks:
                get_gantt_robots_d_graphs('dgraph',
                                          robot_performance,
                                          dir=file_path + '/run_ ' + str(run_info.run_id) +
                                          '/robot_d_graphs/%s' % robot_performance.robot_id)

                get_gif(file_path + '/run_ ' + str(run_info.run_id) + '/robot_d_graphs/%s/' % robot_performance.robot_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment_name', type=str, action='store', help='Experiment_name')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--approach', type=str, action='store', default='tessi-corrective-preempt', help='Approach name')
    group.add_argument('--all', action='store_true')
    args = parser.parse_args()

    config_params = get_config_params(experiment=args.experiment_name)
    experiment_config = config_params.get("experiment")

    robot_ids = config_params.get("fleet")
    dataset_module = config_params.get("dataset_module")
    datasets = config_params.get("datasets")
    bidding_rule = config_params.get("bidder").get("bidding_rule")
    experiments = list()

    logging.basicConfig(level=logging.DEBUG)

    logging.info("Getting results for experiment: %s", args.experiment_name)

    if args.all:
        approaches = config_params.get("approaches")
        for approach in approaches:
            for dataset_name in datasets:
                experiment = get_experiment(args.experiment_name, approach, bidding_rule, robot_ids, dataset_module, dataset_name)
                experiments.append(experiment)
    else:
        for dataset_name in datasets:
            experiment = get_experiment(args.experiment_name, args.approach, bidding_rule, robot_ids, dataset_module, dataset_name)
            experiments.append(experiment)

    for experiment in experiments:
        file_path = experiment.name + "/" + experiment.approach + "/" + experiment.bidding_rule + "/"
        experiment.to_file(file_path)
        plot_task_schedules(experiment, file_path)
        # plot_robots_d_graphs(experiment, file_path)
