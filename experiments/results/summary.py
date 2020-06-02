import argparse
import os
import statistics

import dateutil.parser
from datetime import datetime
import numpy as np
import yaml

from experiments.results.plot.utils import get_dataset_results, max_n_runs
from mrs.config.params import get_config_params
from mrs.utils.as_dict import AsDictMixin


class PerformanceMetrics(AsDictMixin):
    def __init__(self, experiment_name, approach, dataset_name, bidding_rule, max_n_runs):
        self.experiment_name = experiment_name
        self.approach = approach
        self.dataset_name = dataset_name
        self.bidding_rule = bidding_rule
        self.max_n_runs = max_n_runs

        self.number_allocated_tasks = 0
        self.number_unallocated_tasks = 0
        self.number_completed_tasks = 0
        self.number_on_time_tasks = 0
        self.number_delayed_tasks = 0
        self.number_early_tasks = 0

        self.completion_rate = 0
        self.success_rate = 0

        self.total_delay = 0
        self.total_earliness = 0

        self.number_preempted_tasks = 0
        self.number_re_alloced_tasks = 0
        self.number_unsuccessfully_re_allocated_tasks = 0

        self.number_re_allocation_attempts = 0
        self.number_re_allocations = 0

        self.number_re_allocation_attempts_per_task = 0
        self.number_re_allocations_per_task = 0

        self.allocation_time = 0
        self.re_allocation_time = 0
        self.d_graph_re_computation_time = 0
        self.bid_times = dict()

        self.robot_001_usage = 0
        self.robot_002_usage = 0
        self.robot_003_usage = 0
        self.robot_004_usage = 0
        self.robot_005_usage = 0

        self.start_time = 0
        self.finish_time = 0
        self.experiment_time = 0

        self.fleet_work_time = 0
        self.fleet_travel_time = 0
        self.fleet_idle_time = 0

    def to_file(self, file_path, file_name):
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_ = file_path + file_name + ".yaml"
        print("Saving to file: ", file_)

        with open(file_, 'w') as outfile:
            data = self.to_dict()
            yaml.safe_dump(data, outfile, default_flow_style=False)

    def get_avg_performance_metrics(self):
        print("Experiment: ", self.experiment_name)
        print("Dataset: ", self.dataset_name)
        print("Approach: ", self.approach)
        path_to_results = self.experiment_name + '/' + self.approach + '/' + self.bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(self.dataset_name)

        n_runs = 0
        longest_experiment_time = -np.inf

        ###############################################
        number_allocated_tasks = 0
        number_unallocated_tasks = 0
        number_completed_tasks = 0
        number_on_time_tasks = 0
        number_delayed_tasks = 0
        number_early_tasks = 0

        completion_rate = 0
        success_rate = 0

        total_delay = 0
        total_earliness = 0

        number_preempted_tasks = 0
        number_re_alloced_tasks = 0
        number_unsuccessfully_re_allocated_tasks = 0

        number_re_allocation_attempts = 0
        number_re_allocations = 0

        number_re_allocation_attempts_per_task = 0
        number_re_allocations_per_task = 0

        allocation_time = 0
        re_allocation_time = 0
        d_graph_re_computation_time = 0
        bid_times = dict()

        robot_001_usage = 0
        robot_002_usage = 0
        robot_003_usage = 0
        robot_004_usage = 0
        robot_005_usage = 0

        start_times = list()
        finish_times = list()
        experiment_time_acc = 0

        fleet_travel_time = list()
        fleet_work_time = list()
        fleet_idle_time = list()
        ###############################################

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            if n_runs > self.max_n_runs:
                break

            print("Run id: ", run_id)

            metrics = run_info.get("performance_metrics")
            fleet_metrics = metrics.get("fleet_performance_metrics")

            number_allocated_tasks += len(fleet_metrics.get("allocated_tasks"))
            number_unallocated_tasks += len(fleet_metrics.get("unallocated_tasks"))
            number_completed_tasks += len(fleet_metrics.get("completed_tasks"))
            number_on_time_tasks += len(fleet_metrics.get("successful_tasks"))
            number_delayed_tasks += len(fleet_metrics.get("delayed_tasks"))
            number_early_tasks += len(fleet_metrics.get("early_tasks"))

            completion_rate += metrics.get("completion_rate")
            success_rate += metrics.get("success_rate")

            total_delay += fleet_metrics.get("delay")
            total_earliness += fleet_metrics.get("earliness")

            number_preempted_tasks += len(fleet_metrics.get("preempted_tasks"))
            number_re_alloced_tasks += len(fleet_metrics.get("re_allocated_tasks"))
            number_unsuccessfully_re_allocated_tasks += len(fleet_metrics.get("unsuccessfully_re_allocated_tasks"))

            #############################
            attempts = 0
            re_allocations = 0

            n_tasks_attempts = 0
            n_tasks_re_allocations = 0
            attempts_per_task = 0
            re_allocations_per_task = 0

            time_to_allocate = 0
            time_to_re_allocate = 0
            time_to_recompute_d_graph = 0

            travel_time = 0
            work_time = 0
            ###############################

            for task_metrics in fleet_metrics.get("tasks_performance_metrics"):
                attempts += task_metrics.get("n_re_allocation_attempts")
                re_allocations += task_metrics.get("n_re_allocations")

                if task_metrics.get("n_re_allocation_attempts") > 0:
                    n_tasks_attempts += 1
                    attempts_per_task += task_metrics.get("n_re_allocation_attempts")

                if task_metrics.get("n_re_allocations") > 0:
                    n_tasks_re_allocations += 1
                    re_allocations_per_task += task_metrics.get("n_re_allocations")

                time_to_allocate += task_metrics.get('allocation_time')
                time_to_re_allocate += task_metrics.get('re_allocation_time')

            number_re_allocation_attempts += attempts
            number_re_allocations += re_allocations

            if n_tasks_attempts > 0:
                number_re_allocation_attempts_per_task += attempts_per_task / n_tasks_attempts

            if n_tasks_re_allocations > 0:
                number_re_allocations_per_task += re_allocations_per_task/n_tasks_re_allocations

            allocation_time += time_to_allocate
            re_allocation_time += time_to_re_allocate

            start_time = dateutil.parser.parse(metrics['start_time'])
            finish_time = dateutil.parser.parse(metrics['finish_time'])

            experiment_time = (finish_time - start_time).total_seconds()
            experiment_time_acc += experiment_time

            if experiment_time > longest_experiment_time:
                longest_experiment_time = experiment_time

            start_times.append(start_time.timestamp())
            finish_times.append(finish_time.timestamp())

            for robot_metrics in fleet_metrics.get("robots_performance_metrics"):
                time_to_recompute_d_graph += robot_metrics.get("dgraph_recomputation_time")

                if robot_metrics.get("robot_id") == "robot_001":
                    robot_001_usage += robot_metrics["usage"]
                if robot_metrics.get("robot_id") == "robot_002":
                    robot_002_usage += robot_metrics["usage"]
                if robot_metrics.get("robot_id") == "robot_003":
                    robot_003_usage += robot_metrics["usage"]
                if robot_metrics.get("robot_id") == "robot_004":
                    robot_004_usage += robot_metrics["usage"]
                if robot_metrics.get("robot_id") == "robot_005":
                    robot_005_usage += robot_metrics["usage"]

                if robot_metrics.get("time_distribution"):
                    travel_time += robot_metrics.get("time_distribution").get("travel_time")
                    work_time += robot_metrics.get("time_distribution").get("work_time")

            d_graph_re_computation_time += time_to_recompute_d_graph

            fleet_travel_time.append(travel_time)
            fleet_work_time.append(work_time)
            fleet_idle_time.append(0)

            for n_tasks, time_to_bid in fleet_metrics.get("bid_times").items():
                if n_tasks not in bid_times:
                    bid_times[n_tasks] = list()
                bid_times[n_tasks].append(time_to_bid)

        # Taking the average

        self.number_allocated_tasks = number_allocated_tasks/self.max_n_runs
        self.number_unallocated_tasks = number_unallocated_tasks/self.max_n_runs
        self.number_completed_tasks = number_completed_tasks/self.max_n_runs
        self.number_on_time_tasks = number_on_time_tasks/self.max_n_runs
        self.number_delayed_tasks = number_delayed_tasks/self.max_n_runs
        self.number_early_tasks = number_early_tasks/self.max_n_runs

        self.completion_rate = completion_rate/self.max_n_runs
        self.success_rate = success_rate/self.max_n_runs

        self.total_delay = total_delay/self.max_n_runs
        self.total_earliness = total_earliness/self.max_n_runs

        self.number_preempted_tasks = number_preempted_tasks/self.max_n_runs
        self.number_re_alloced_tasks = number_re_alloced_tasks/self.max_n_runs
        self.number_unsuccessfully_re_allocated_tasks = number_unsuccessfully_re_allocated_tasks/self.max_n_runs

        self.number_re_allocation_attempts = number_re_allocation_attempts/self.max_n_runs
        self.number_re_allocations = number_re_allocations/self.max_n_runs

        self.number_re_allocation_attempts_per_task = number_re_allocation_attempts_per_task/self.max_n_runs
        self.number_re_allocations_per_task = number_re_allocations_per_task/self.max_n_runs

        self.allocation_time = allocation_time/self.max_n_runs
        self.re_allocation_time = re_allocation_time/self.max_n_runs
        self.d_graph_re_computation_time = d_graph_re_computation_time/self.max_n_runs

        for n_tasks, times_to_bid in bid_times.items():
            self.bid_times[n_tasks] = statistics.mean(times_to_bid)

        self.robot_001_usage = robot_001_usage/self.max_n_runs
        self.robot_002_usage = robot_002_usage/self.max_n_runs
        self.robot_003_usage = robot_003_usage/self.max_n_runs
        self.robot_004_usage = robot_004_usage/self.max_n_runs
        self.robot_005_usage = robot_005_usage/self.max_n_runs

        fleet_total_time = longest_experiment_time * len(robot_metrics)

        for i, travel_time in enumerate(fleet_travel_time):
            fleet_travel_time[i] = 100 * travel_time / fleet_total_time

        for i, work_time in enumerate(fleet_work_time):
            fleet_work_time[i] = 100 * work_time / fleet_total_time
            fleet_idle_time[i] = 100 - (fleet_work_time[i] + fleet_travel_time[i])

        self.fleet_work_time = statistics.mean(fleet_work_time)
        self.fleet_travel_time = statistics.mean(fleet_travel_time)
        self.fleet_idle_time = statistics.mean(fleet_idle_time)

        start_time = statistics.mean(start_times)
        self.start_time = datetime.fromtimestamp(start_time).isoformat()

        finish_time = statistics.mean(finish_times)
        self.finish_time = datetime.fromtimestamp(finish_time).isoformat()

        self.experiment_time = experiment_time_acc/self.max_n_runs  #finish_time - start_time


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment_name', type=str, action='store', help='Experiment_name')
    parser.add_argument('recovery_method', type=str, action='store', help='Recovery method',
                        choices=['preempt', 're-allocate'])

    parser.add_argument('--bidding_rule', type=str, action='store', default='completion_time')
    parser.add_argument('--max_n_runs', type=int, action='store', default=max_n_runs)

    args = parser.parse_args()

    config_params = get_config_params(experiment=args.experiment_name)
    approaches = config_params.get("approaches")
    datasets = config_params.get("datasets")
    dataset_module = config_params.get("dataset_module")

    approaches_recovery_method = [a for a in approaches if args.recovery_method in a]

    for dataset in datasets:
        for approach in approaches_recovery_method:
            performance_metrics = PerformanceMetrics(args.experiment_name, approach, dataset, args.bidding_rule, args.max_n_runs)
            performance_metrics.get_avg_performance_metrics()

            file_path = args.experiment_name + "/" + approach + "/" + args.bidding_rule + "/summary/"
            file_name = "summary_" + dataset
            performance_metrics.to_file(file_path, file_name)
