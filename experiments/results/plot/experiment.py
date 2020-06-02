import argparse
import statistics
from datetime import datetime

import dateutil.parser
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

from experiments.results.plot.utils import get_dataset_results, save_plot, set_box_color, get_meanprops, get_title, \
    get_plot_path, ticks, max_n_runs, get_flierprops
from mrs.config.params import get_config_params
from mrs.utils.utils import load_yaml_file_from_module


# Based on:
# https://stackoverflow.com/questions/16592222/matplotlib-group-boxplots
# https://stackoverflow.com/questions/10101700/moving-matplotlib-legend-outside-of-the-axis-makes-it-cutoff-by-the-figure-box
# https://matplotlib.org/3.1.1/gallery/statistics/boxplot_demo.html
# https://stackoverflow.com/questions/12998430/remove-xticks-in-a-matplotlib-plot


def box_plot_robot_usage(experiment_name, recovery_method, approaches, dataset_name, bidding_rule):
    print("Robot usage")
    title = get_title(experiment_name, recovery_method, dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "robot_usage_" + recovery_method + '_' + dataset_name
    approaches_recovery_method = [a for a in approaches if recovery_method in a]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)
    usage_robot_1 = list()
    usage_robot_2 = list()
    usage_robot_3 = list()
    usage_robot_4 = list()
    usage_robot_5 = list()

    for i, approach in enumerate(approaches_recovery_method):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        approach_usage_robot_1 = list()
        approach_usage_robot_2 = list()
        approach_usage_robot_3 = list()
        approach_usage_robot_4 = list()
        approach_usage_robot_5 = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            print("Run: ", n_runs)
            if n_runs > max_n_runs:
                break

            robot_metrics = run_info.get("performance_metrics").get("fleet_performance_metrics").get(
                "robots_performance_metrics")
            for robot in robot_metrics:
                if robot.get("robot_id") == "robot_001":
                    approach_usage_robot_1.append(robot["usage"])
                if robot.get("robot_id") == "robot_002":
                    approach_usage_robot_2.append(robot["usage"])
                if robot.get("robot_id") == "robot_003":
                    approach_usage_robot_3.append(robot["usage"])
                if robot.get("robot_id") == "robot_004":
                    approach_usage_robot_4.append(robot["usage"])
                if robot.get("robot_id") == "robot_005":
                    approach_usage_robot_5.append(robot["usage"])

        usage_robot_1 += [approach_usage_robot_1]
        usage_robot_2 += [approach_usage_robot_2]
        usage_robot_3 += [approach_usage_robot_3]
        usage_robot_4 += [approach_usage_robot_4]
        usage_robot_5 += [approach_usage_robot_5]

    bp1 = ax.boxplot(usage_robot_1, positions=np.array(range(len(usage_robot_1))) * 6, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#3182bd'), flierprops=get_flierprops('#3182bd'))
    bp2 = ax.boxplot(usage_robot_2, positions=np.array(range(len(usage_robot_2))) * 6 + 1, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca25f'), flierprops=get_flierprops('#2ca25f'))
    bp3 = ax.boxplot(usage_robot_3, positions=np.array(range(len(usage_robot_3))) * 6 + 2, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#f03b20'), flierprops=get_flierprops('#f03b20'))
    bp4 = ax.boxplot(usage_robot_4, positions=np.array(range(len(usage_robot_4))) * 6 + 3, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#756bb1'), flierprops=get_flierprops('#756bb1'))
    bp5 = ax.boxplot(usage_robot_5, positions=np.array(range(len(usage_robot_5))) * 6 + 4, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#7fcdbb'), flierprops=get_flierprops('#7fcdbb'))

    set_box_color(bp1, '#3182bd')
    set_box_color(bp2, '#2ca25f')
    set_box_color(bp3, '#f03b20')
    set_box_color(bp4, '#756bb1')
    set_box_color(bp5, '#7fcdbb')

    plt.plot([], c='#3182bd', label='Robot 001', linewidth=2)
    plt.plot([], c='#2ca25f', label='Robot 002', linewidth=2)
    plt.plot([], c='#f03b20', label='Robot 003', linewidth=2)
    plt.plot([], c='#756bb1', label='Robot 004', linewidth=2)
    plt.plot([], c='#7fcdbb', label='Robot 005', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=5, fancybox=True, shadow=True)


    # ax.set_ylim(-1, 51)
    # ax.set_yticks(list(range(0, 60, 10)))
    # ymin, ymax = ax.get_ylim()
    ymin = 0
    ymax = 35
    plt.ylim(ymin, ymax)

    plt.vlines(5, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(11, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(17, ymin=ymin, ymax=ymax, linewidths=1)
    # plt.ylim(ymin, ymax)
    plt.yticks(list(range(0, 35, 5)))

    ax.set_ylabel("Completed tasks(%)")
    # ax.set_title(title)
    ax.yaxis.grid()

    plt.xticks(range(1, (len(ticks) * 6)-1, 6), ticks)
    plt.xlim(-1, len(ticks) * 6-1)
    plt.tight_layout()
    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_set_distribution(experiment_name, recovery_method, approaches, dataset_name, dataset_module, bidding_rule):
    print("Set distribution")
    save_in_path = get_plot_path(experiment_name)
    plot_name = "set_distribution" + recovery_method + '_' + dataset_name
    approaches_recovery_method = [a for a in approaches if recovery_method in a]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)
    distribution_robot_1 = list()
    distribution_robot_2 = list()
    distribution_robot_3 = list()
    distribution_robot_4 = list()
    distribution_robot_5 = list()

    dataset_dict = load_yaml_file_from_module(dataset_module, dataset_name + '.yaml')
    tasks_dict = dataset_dict.get('tasks')

    for i, approach in enumerate(approaches_recovery_method):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        approach_distribution_robot_1 = list()
        approach_distribution_robot_2 = list()
        approach_distribution_robot_3 = list()
        approach_distribution_robot_4 = list()
        approach_distribution_robot_5 = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            print("Run: ", n_runs)
            if n_runs > max_n_runs:
                break

            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
            robot_metrics = metrics.get("robots_performance_metrics")

            for robot in robot_metrics:
                set_numbers = list()
                for robot_task in robot.get("robot_tasks"):
                    task = tasks_dict.get(robot_task)
                    if task.get("set_number") not in set_numbers:
                        set_numbers.append(task.get("set_number"))

                if robot.get("robot_id") == "robot_001":
                    approach_distribution_robot_1.append(len(set_numbers))
                if robot.get("robot_id") == "robot_002":
                    approach_distribution_robot_2.append(len(set_numbers))
                if robot.get("robot_id") == "robot_003":
                    approach_distribution_robot_3.append(len(set_numbers))
                if robot.get("robot_id") == "robot_004":
                    approach_distribution_robot_4.append(len(set_numbers))
                if robot.get("robot_id") == "robot_005":
                    approach_distribution_robot_5.append(len(set_numbers))

            print("robot 1: ", approach_distribution_robot_1)
            print("robot 2: ", approach_distribution_robot_2)
            print("robot 3: ", approach_distribution_robot_3)
            print("robot 4: ", approach_distribution_robot_4)
            print("robot 5: ", approach_distribution_robot_5)

        distribution_robot_1 += [approach_distribution_robot_1]
        distribution_robot_2 += [approach_distribution_robot_2]
        distribution_robot_3 += [approach_distribution_robot_3]
        distribution_robot_4 += [approach_distribution_robot_4]
        distribution_robot_5 += [approach_distribution_robot_5]

    bp1 = ax.boxplot(distribution_robot_1, positions=np.array(range(len(distribution_robot_1))) * 6, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#3182bd'),
                     flierprops=get_flierprops('#3182bd'))
    bp2 = ax.boxplot(distribution_robot_2, positions=np.array(range(len(distribution_robot_2))) * 6 + 1, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca25f'),
                     flierprops=get_flierprops('#2ca25f'))
    bp3 = ax.boxplot(distribution_robot_3, positions=np.array(range(len(distribution_robot_3))) * 6 + 2, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#f03b20'),
                     flierprops=get_flierprops('#f03b20'))
    bp4 = ax.boxplot(distribution_robot_4, positions=np.array(range(len(distribution_robot_4))) * 6 + 3, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#756bb1'),
                     flierprops=get_flierprops('#756bb1'))
    bp5 = ax.boxplot(distribution_robot_5, positions=np.array(range(len(distribution_robot_5))) * 6 + 4, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#7fcdbb'),
                     flierprops=get_flierprops('#7fcdbb'))

    set_box_color(bp1, '#3182bd')
    set_box_color(bp2, '#2ca25f')
    set_box_color(bp3, '#f03b20')
    set_box_color(bp4, '#756bb1')
    set_box_color(bp5, '#7fcdbb')

    plt.plot([], c='#3182bd', label='Robot 001', linewidth=2)
    plt.plot([], c='#2ca25f', label='Robot 002', linewidth=2)
    plt.plot([], c='#f03b20', label='Robot 003', linewidth=2)
    plt.plot([], c='#756bb1', label='Robot 004', linewidth=2)
    plt.plot([], c='#7fcdbb', label='Robot 005', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=5, fancybox=True, shadow=True)

    ymin, ymax = ax.get_ylim()
    plt.vlines(5, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(11, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(17, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    ax.set_ylabel("Number of set of tasks")
    ax.yaxis.grid()

    plt.xticks(range(1, (len(ticks) * 6) - 1, 6), ticks)
    plt.xlim(-1, len(ticks) * 6 - 1)
    plt.tight_layout()
    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_times(experiment_name, recovery_method, approaches, dataset_name, bidding_rule):
    print("Plot times")
    title = get_title(experiment_name, recovery_method, dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "times_" + recovery_method + '_' + dataset_name
    approaches_recovery_method = [a for a in approaches if recovery_method in a]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    allocation_times = list()
    re_allocation_times = list()
    dgraph_recomputation_times = list()

    for i, approach in enumerate(approaches_recovery_method):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        approach_allocation_times = list()
        approach_re_allocation_times = list()
        approach_dgraph_recomputation_times = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            print("Run: ", n_runs)
            if n_runs > max_n_runs:
                break

            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
            allocation_time = 0
            re_allocation_time = 0
            dgraph_recomputation_time = 0

            for task_performance in metrics.get("tasks_performance_metrics"):
                allocation_time += task_performance.get('allocation_time')
                re_allocation_time += task_performance.get('re_allocation_time')

            for robot_performance in metrics.get("robots_performance_metrics"):
                dgraph_recomputation_time += robot_performance.get("dgraph_recomputation_time")

            approach_allocation_times.append(allocation_time)
            approach_re_allocation_times.append(re_allocation_time)
            approach_dgraph_recomputation_times.append(dgraph_recomputation_time)

        allocation_times += [approach_allocation_times]
        re_allocation_times += [approach_re_allocation_times]
        dgraph_recomputation_times += [approach_dgraph_recomputation_times]

    bp1 = ax.boxplot(allocation_times, positions=np.array(range(len(allocation_times))) * 4, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#4376b8'), flierprops=get_flierprops('#4376b8'))
    bp2 = ax.boxplot(re_allocation_times, positions=np.array(range(len(re_allocation_times))) * 4 + 1, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#399b5e'), flierprops=get_flierprops('#399b5e'))

    bp3 = ax.boxplot(dgraph_recomputation_times, positions=np.array(range(len(dgraph_recomputation_times))) * 4 + 2, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#FFC300'), flierprops=get_flierprops('#FFC300'))

    set_box_color(bp1, '#4376b8')
    set_box_color(bp2, '#399b5e')
    set_box_color(bp3, '#FFC300')

    plt.plot([], c='#4376b8', label='Allocation time', linewidth=2)
    plt.plot([], c='#399b5e', label='Re-allocation time', linewidth=2)
    plt.plot([], c='#FFC300', label='DGraph re-computation time', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, fancybox=True, shadow=True)

    ax.set_ylim(bottom=-1)
    ymin, ymax = ax.get_ylim()

    plt.vlines(3, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(7, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(11, ymin=ymin, ymax=ymax, linewidths=1)

    plt.xticks(range(1, (len(ticks) * 4)-1, 4), ticks)
    plt.xlim(-1, len(ticks) * 4 - 1)
    plt.tight_layout()
    # ax.set_title(title)
    ax.set_ylabel('Time (seconds)')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_allocations(experiment_name, recovery_method, approaches, dataset_name, bidding_rule):
    print("Allocations")
    title = get_title(experiment_name, recovery_method, dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "allocations_" + recovery_method + '_' + dataset_name
    approaches_recovery_method = [a for a in approaches if recovery_method in a]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    allocated_tasks = list()
    unallocated_tasks = list()
    preempted_tasks = list()
    re_allocated_tasks = list()
    unsuccessfully_re_allocated_tasks = list()

    for i, approach in enumerate(approaches_recovery_method):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        approach_allocated_tasks = list()
        approach_unallocated_tasks = list()
        approach_preempted_tasks = list()
        approach_re_allocated_tasks = list()
        approach_unsuccessfully_re_allocated_tasks = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            print("Run: ", n_runs)
            if n_runs > max_n_runs:
                break

            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
            approach_allocated_tasks.append(len(metrics.get("allocated_tasks")))
            approach_unallocated_tasks.append(len(metrics.get("unallocated_tasks")))
            approach_preempted_tasks.append(len(metrics.get("preempted_tasks")))
            approach_re_allocated_tasks.append(len(metrics.get("re_allocated_tasks")))
            approach_unsuccessfully_re_allocated_tasks.append(len(metrics.get("unsuccessfully_re_allocated_tasks")))

        allocated_tasks += [approach_allocated_tasks]
        unallocated_tasks += [approach_unallocated_tasks]
        preempted_tasks += [approach_preempted_tasks]
        re_allocated_tasks += [approach_re_allocated_tasks]
        unsuccessfully_re_allocated_tasks += [approach_unsuccessfully_re_allocated_tasks]

    if recovery_method == 'preempt':
        bp1 = ax.boxplot(allocated_tasks, positions=np.array(range(len(allocated_tasks))) * 4, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#3333ff'),
                         flierprops=get_flierprops('#3333ff'))
        bp2 = ax.boxplot(unallocated_tasks, positions=np.array(range(len(unallocated_tasks))) * 4 + 1, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#ff3333'),
                         flierprops=get_flierprops('#ff3333'))

        bp3 = ax.boxplot(preempted_tasks, positions=np.array(range(len(preempted_tasks))) * 4 + 2, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#ffb733'),
                         flierprops=get_flierprops('#ffb733'))

        set_box_color(bp1, '#3333ff')
        set_box_color(bp2, '#ff3333')
        set_box_color(bp3, '#ffb733')

        plt.plot([], c='#3333ff', label='Allocated', linewidth=2)
        plt.plot([], c='#ff3333', label='Unallocated', linewidth=2)
        plt.plot([], c='#ffb733', label='Preempted', linewidth=2)

        plt.vlines(3, ymin=-1, ymax=26, linewidths=1)
        plt.vlines(7, ymin=-1, ymax=26, linewidths=1)
        plt.vlines(11, ymin=-1, ymax=26, linewidths=1)

        plt.xticks(range(1, (len(ticks) * 4) - 1, 4), ticks)
        plt.xlim(-1, len(ticks) * 4 - 1)
        lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, fancybox=True, shadow=True)

    else:
        bp1 = ax.boxplot(allocated_tasks, positions=np.array(range(len(allocated_tasks))) * 5, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#3333ff'),
                         flierprops=get_flierprops('#3333ff'))
        bp2 = ax.boxplot(unallocated_tasks, positions=np.array(range(len(unallocated_tasks))) * 5 + 1, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#ff3333'),
                         flierprops=get_flierprops('#ff3333'))

        bp3 = ax.boxplot(re_allocated_tasks, positions=np.array(range(len(re_allocated_tasks))) * 5 + 2, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#399b5e'),
                         flierprops=get_flierprops('#399b5e'))

        bp4 = ax.boxplot(unsuccessfully_re_allocated_tasks,
                         positions=np.array(range(len(unsuccessfully_re_allocated_tasks))) * 5 + 3, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#ffb733'),
                         flierprops=get_flierprops('#ffb733'))

        set_box_color(bp1, '#3333ff')
        set_box_color(bp2, '#ff3333')
        set_box_color(bp3, '#399b5e')
        set_box_color(bp4, '#ffb733')

        plt.plot([], c='#3333ff', label='Allocated', linewidth=2)
        plt.plot([], c='#ff3333', label='Unallocated', linewidth=2)
        plt.plot([], c='#399b5e', label='Re-allocated', linewidth=2)
        plt.plot([], c='#ffb733', label='Unsuccessfully re-allocated', linewidth=2)

        plt.vlines(4, ymin=-1, ymax=26, linewidths=1)
        plt.vlines(9, ymin=-1, ymax=26, linewidths=1)
        plt.vlines(14, ymin=-1, ymax=26, linewidths=1)

        plt.xticks(range(1, len(ticks) * 5, 5), ticks)
        plt.xlim(-1, len(ticks) * 4 + 3)
        lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    ax.set_ylim(-1, 26)
    ax.set_yticks(list(range(0, 26, 5)))

    ax.set_ylabel("Number of tasks")
    # ax.set_title(title)
    ax.yaxis.grid()
    plt.tight_layout()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_fleet_time_distribution(experiment_name, recovery_method, approaches, dataset_name, bidding_rule):
    print("Fleet time distribution")
    title = get_title(experiment_name, recovery_method, dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "fleet_time_" + recovery_method + '_' + dataset_name

    approaches_recovery_method = [a for a in approaches if recovery_method in a]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    fleet_travel_time = list()
    fleet_work_time = list()
    fleet_idle_time = list()

    longest_experiment_time = -np.inf

    n_robots = 5

    for i, approach in enumerate(approaches_recovery_method):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        approach_travel_time = list()
        approach_work_time = list()
        approach_idle_time = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            print("Run: ", n_runs)
            if n_runs > max_n_runs:
                break

            metrics = run_info.get("performance_metrics")
            start_time = dateutil.parser.parse(metrics['start_time'])
            finish_time = dateutil.parser.parse(metrics['finish_time'])
            experiment_time = (finish_time - start_time).total_seconds()
            if experiment_time > longest_experiment_time:
                longest_experiment_time = experiment_time

            robot_metrics = metrics.get("fleet_performance_metrics").get("robots_performance_metrics")
            travel_time = 0
            work_time = 0

            for robot in robot_metrics:
                if robot.get("time_distribution"):
                    travel_time += robot.get("time_distribution").get("travel_time")
                    work_time += robot.get("time_distribution").get("work_time")

            approach_travel_time.append(travel_time)
            approach_work_time.append(work_time)
            approach_idle_time.append(0)

        fleet_travel_time += [approach_travel_time]
        fleet_work_time += [approach_work_time]
        fleet_idle_time += [approach_idle_time]

    for i, approach_runs in enumerate(fleet_idle_time):
        for j, idle_time in enumerate(approach_runs):
            fleet_idle_time[i][j] = (longest_experiment_time*n_robots) - (fleet_work_time[i][j] +fleet_travel_time[i][j])

    for i, approach_runs in enumerate(fleet_travel_time):
        for j, travel_time in enumerate(approach_runs):
            fleet_travel_time[i][j] = 100*travel_time / (longest_experiment_time*n_robots)

    for i, approach_runs in enumerate(fleet_work_time):
        for j, work_time in enumerate(approach_runs):
            fleet_work_time[i][j] = 100*work_time / (longest_experiment_time*n_robots)
            # fleet_idle_time[i][j] = 100 - (fleet_work_time[i][j] + fleet_travel_time[i][j])

    for i, approach_runs in enumerate(fleet_idle_time):
        for j, idle_time in enumerate(approach_runs):
            fleet_idle_time[i][j] = 100*idle_time / (longest_experiment_time*n_robots)

    bp1 = ax.boxplot(fleet_travel_time, positions=np.array(range(len(fleet_travel_time))) * 4, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#4376b8'), flierprops=get_flierprops('#4376b8'))
    bp2 = ax.boxplot(fleet_work_time, positions=np.array(range(len(fleet_work_time))) * 4 + 1, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#399b5e'), flierprops=get_flierprops('#399b5e'))

    bp3 = ax.boxplot(fleet_idle_time, positions=np.array(range(len(fleet_idle_time))) * 4 + 2, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#FFC300'), flierprops=get_flierprops('#FFC300'))

    set_box_color(bp1, '#4376b8')
    set_box_color(bp2, '#399b5e')
    set_box_color(bp3, '#FFC300')

    plt.plot([], c='#4376b8', label='Travel time', linewidth=2)
    plt.plot([], c='#399b5e', label='Work time', linewidth=2)
    plt.plot([], c='#FFC300', label='Idle time', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, fancybox=True, shadow=True)

    # ax.set_yticks(list(range(0, 110, 10)))
    # ymin, ymax = ax.get_ylim()
    ymin = 0
    ymax = 80
    plt.ylim(ymin, ymax)

    plt.vlines(3, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(7, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(11, ymin=ymin, ymax=ymax, linewidths=1)
    # plt.ylim(ymin, ymax)
    ax.set_yticks(list(range(0, 80, 10)))

    ax.set_ylabel("Percentage (%)")
    # ax.set_title(title)
    ax.yaxis.grid()

    plt.xticks(range(1, (len(ticks) * 4)-1, 4), ticks)
    plt.xlim(-1, len(ticks) * 4 - 1)
    plt.tight_layout()
    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_amount_of_delay(experiment_name, recovery_method, approaches, dataset_name, bidding_rule):
    """
    - Amount of delays (s)
    - Amount of earliness (s)
    """
    print("Amount of delay")
    title = get_title(experiment_name, recovery_method, dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "slack_" + recovery_method + '_' + dataset_name

    approaches_recovery_method = [a for a in approaches if recovery_method in a]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    delay = list()
    earliness = list()
    for i, approach in enumerate(approaches_recovery_method):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        run_delay = list()
        run_earliness = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            print("Run: ", n_runs)
            if n_runs > max_n_runs:
                break

            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
            run_delay.append(metrics.get("delay"))
            run_earliness.append(metrics.get("earliness"))

        delay += [run_delay]
        earliness += [run_earliness]

    bp1 = ax.boxplot(delay, positions=np.array(range(len(delay))) * 3, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff3333'), flierprops=get_flierprops('#ff3333'))
    bp2 = ax.boxplot(earliness, positions=np.array(range(len(earliness))) * 3 + 1, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ffb733'), flierprops=get_flierprops('#ffb733'))

    set_box_color(bp1, '#ff3333')
    set_box_color(bp2, '#ffb733')

    plt.plot([], c='#ff3333', label='Delayed', linewidth=2)
    plt.plot([], c='#ffb733', label='Early', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fancybox=True, shadow=True)

    # ax.set_ylim(bottom=-1)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    plt.xticks(range(1, (len(ticks) * 3)-1, 3), ticks)
    plt.xlim(-1, len(ticks) * 3-1)
    plt.tight_layout()
    # ax.set_title(title)
    ax.set_ylabel('Time [s]')
    ax.yaxis.grid()
    plt.tight_layout()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    # ymin, ymax = ax.get_ylim()
    # print("ymax: ", ymax)
    ymin = -0.5
    ymax = 1170
    plt.ylim(ymin, ymax)

    plt.vlines(2, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(5, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(8, ymin=ymin, ymax=ymax, linewidths=1)
    # plt.ylim(ymin, ymax)
    plt.yticks(list(range(0, 1170, 150)))

    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_re_allocation_info(experiment_name, approaches, dataset_name, bidding_rule):
    """ Plots re-allocation information:
    - Number of re-allocation attempts
    - Number of re-allocations (e.g. successful attempts)

    Use only for experiments with recovery method 're-allocation'
    """
    print("Re-allocation")
    title = get_title(experiment_name, 're-allocation', dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "re_allocation_metrics_" + dataset_name

    re_allocation_attempts = list()
    re_allocations = list()  # Percentage of re allocation attempts that were successful

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)  # Number of tasks

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        approach_re_allocation_attempts = list()
        approach_re_allocations = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            if n_runs > max_n_runs:
                break
            print("Run: ", n_runs)

            n_re_allocation_attempts = 0
            n_re_allocations = 0

            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

            for task_metrics in metrics.get("tasks_performance_metrics"):
                n_re_allocation_attempts += task_metrics.get("n_re_allocation_attempts")
                n_re_allocations += task_metrics.get("n_re_allocations")

            approach_re_allocation_attempts.append(n_re_allocation_attempts)
            approach_re_allocations.append(n_re_allocations)

        re_allocation_attempts += [approach_re_allocation_attempts]
        re_allocations += [approach_re_allocations]

    bp1 = ax.boxplot(re_allocation_attempts, positions=np.array(range(len(re_allocation_attempts))) * 3,  widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#4376b8'), flierprops=get_flierprops('#4376b8'))
    bp2 = ax.boxplot(re_allocations, positions=np.array(range(len(re_allocations))) * 3+1,  widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#399b5e'), flierprops=get_flierprops('#399b5e'))

    set_box_color(bp1, '#4376b8')
    set_box_color(bp2, '#399b5e')

    plt.plot([], c='#4376b8', label='Re-allocation attempts', linewidth=2)
    plt.plot([], c='#399b5e', label='Re-allocations', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fancybox=True, shadow=True)

    # ymin, ymax = ax.get_ylim()
    ymin = -0.5
    ymax = 26
    plt.ylim(ymin, ymax)

    plt.vlines(2, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(5, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(8, ymin=ymin, ymax=ymax, linewidths=1)
    # plt.ylim(ymin, ymax)
    plt.yticks(list(range(0, 27, 2)))

    # ax.set_title(title)
    # ax.set_ylabel('Number of tasks')
    ax.yaxis.grid()

    plt.xticks(range(0, len(ticks) * 3, 3), ticks)
    plt.xlim(-1, len(ticks) * 3-1)
    plt.tight_layout()

    ax.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_re_allocation_per_task_info(experiment_name, approaches, dataset_name, bidding_rule):
    """ Plots re-allocation information:
    - Number of re-allocation attempts per task
    - Number of re-allocations per task

    Use only for experiments with recovery method 're-allocation'
    """
    print("Re-allocation")
    title = get_title(experiment_name, 're-allocation', dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "re_allocation_metrics_per_task_" + dataset_name

    re_allocation_attempts_per_task = list()
    re_allocations_per_task = list()  # Percentage of re allocation attempts that were successful

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)  # Number of tasks

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        approach_re_allocation_attempts_per_task = list()
        approach_re_allocations_per_task = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            print("Run: ", n_runs)
            if n_runs > max_n_runs:
                break

            n_re_allocation_attempts = 0
            n_re_allocations = 0
            n_tasks = 0

            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

            for task_metrics in metrics.get("tasks_performance_metrics"):
                if task_metrics.get("n_re_allocation_attempts") > 0:
                    n_tasks += 1
                    n_re_allocation_attempts += task_metrics.get("n_re_allocation_attempts")
                    n_re_allocations += task_metrics.get("n_re_allocations")

            if n_tasks > 0:
                approach_re_allocation_attempts_per_task.append(n_re_allocation_attempts/n_tasks)
                approach_re_allocations_per_task.append(n_re_allocations/n_tasks)

        re_allocation_attempts_per_task += [approach_re_allocation_attempts_per_task]
        re_allocations_per_task += [approach_re_allocations_per_task]

    bp1 = ax.boxplot(re_allocation_attempts_per_task, positions=np.array(range(len(re_allocation_attempts_per_task))) * 3,  widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#4376b8'), flierprops=get_flierprops('#4376b8'))
    bp2 = ax.boxplot(re_allocations_per_task, positions=np.array(range(len(re_allocations_per_task))) * 3+1,  widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#399b5e'), flierprops=get_flierprops('#399b5e'))

    set_box_color(bp1, '#4376b8')
    set_box_color(bp2, '#399b5e')

    plt.plot([], c='#4376b8', label='Re-allocation attempts per task', linewidth=2)
    plt.plot([], c='#399b5e', label='Re-allocations per task', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fancybox=True, shadow=True)

    ymin, ymax = ax.get_ylim()
    plt.vlines(2, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(5, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(8, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)
    # ax.set_ylabel('Number of tasks')
    ax.yaxis.grid()

    plt.xticks(range(0, len(ticks) * 3, 3), ticks)
    plt.xlim(-1, len(ticks) * 3-1)
    plt.tight_layout()

    ax.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_re_allocation_info(experiment_name, approaches, dataset_name, bidding_rule):
    """ Plots re-allocation information:
    - Number of re-allocation attempts
    - Number of re-allocations (e.g. successful attempts)
    - Re-allocation time (for successful attempts)

    Use only for experiments with recovery method 're-allocation'
    """
    title = get_title(experiment_name, 're-allocation', dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "re_allocation_metrics_bar" + dataset_name

    index = np.arange(len(approaches))
    bar_width = 0.2
    opacity = 0.8

    avgs_re_allocation_attempts = list()
    avgs_re_allocations = list()
    avgs_re_allocation_times = list()

    stdevs_re_allocation_attempts = list()
    stdevs_re_allocations = list()
    stdevs_re_allocation_times = list()

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)  # Number of tasks
    ax2 = ax.twinx()  # Time (s)

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        re_allocation_attempts = list()
        re_allocations = list()
        re_allocation_times = list()

        for run_id, run_info in results.get("runs").items():
            print("run_id: ", run_id)
            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
            successful_reallocations = len(metrics.get("re_allocated_tasks"))
            unsucessful_reallocations = len(metrics.get("unsuccessfully_re_allocated_tasks"))

            re_allocation_attempts.append(successful_reallocations + unsucessful_reallocations)
            re_allocations.append(successful_reallocations)

            for task_performance in metrics.get("tasks_performance_metrics"):
                if task_performance.get('task_id') in metrics.get("re_allocated_tasks"):
                    re_allocation_times.append(task_performance.get('re_allocation_time'))

        print("re_allocation_attempts: ", re_allocation_attempts)
        print("re_allocations: ", re_allocations)
        print("re_allocation_times: ", re_allocation_times)

        if re_allocation_attempts:
            avg_re_allocation_attemps = sum(re_allocation_attempts)/len(re_allocation_attempts)
            stdev_re_allocation_attempts = statistics.stdev(re_allocation_attempts)
        else:
            avg_re_allocation_attemps = 0
            stdev_re_allocation_attempts = 0

        if re_allocations:
            avg_re_allocations = sum(re_allocations)/len(re_allocations)
            stdev_re_allocations = statistics.stdev(re_allocations)
        else:
            avg_re_allocations = 0
            stdev_re_allocations = 0

        if re_allocation_times:
            avg_re_allocation_times = sum(re_allocation_times)/len(re_allocation_times)
            stdev_re_allocation_times = statistics.stdev(re_allocation_times)
        else:
            avg_re_allocation_times = 0
            stdev_re_allocation_times = 0

        print('avg_re_allocation_attemps', avg_re_allocation_attemps)
        print('avg_re_allocations', avg_re_allocations)
        print('avg_re_allocation_times', avg_re_allocation_times)

        avgs_re_allocation_attempts.append(avg_re_allocation_attemps)
        avgs_re_allocations.append(avg_re_allocations)
        avgs_re_allocation_times.append(avg_re_allocation_times)

        stdevs_re_allocation_attempts.append(stdev_re_allocation_attempts)
        stdevs_re_allocations.append(stdev_re_allocations)
        stdevs_re_allocation_times.append(stdev_re_allocation_times)

    ax2.bar(index + 2*bar_width, avgs_re_allocation_times, bar_width, alpha=opacity, color='#FFC300', label='Re-allocation time',
            yerr=stdevs_re_allocation_times)
    ax.bar(index, avgs_re_allocation_attempts, bar_width, alpha=opacity, color='#4376b8', label='Re-allocation attempts',
           yerr=stdevs_re_allocation_attempts)
    ax.bar(index + bar_width, avgs_re_allocations, bar_width, alpha=opacity, color='#399b5e', label='Re-allocations',
           yerr=stdevs_re_allocations)

    ax2.set_ylabel('Time (seconds)')
    # ax.set_title(title)
    ax.set_ylim(0, 25)
    ax.set_ylabel('Number of tasks')
    ax.set_xlabel('Approaches')

    ax2.legend()
    ax.legend()

    plt.xticks(index + bar_width, ('TeSSI', 'TeSSI-DREA', 'TeSSI-SREA', 'TeSSI-DSC'))
    plt.autoscale()
    # plt.gcf().subplots_adjust(up=0.5)
    # plt.tight_layout()

    save_plot(fig, plot_name, save_in_path)


def bar_plot_completed_tasks(experiment_name, recovery_method, approaches, dataset_name, bidding_rule):
    """ Plots per approach and recovery method
        - avg number of completed tasks
        - avg number of on time tasks
        - avg number of delayed tasks
        - avg number of early tasks
    """
    title = get_title(experiment_name, recovery_method, dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "completed_tasks_" + recovery_method + '_' + dataset_name

    approaches_recovery_method = [a for a in approaches if recovery_method in a]

    index = np.arange(len(approaches_recovery_method))
    bar_width = 0.2
    opacity = 0.8

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    avgs_completed_tasks = list()
    avgs_ontime_tasks = list()
    avgs_delayed_tasks = list()
    avgs_early_tasks = list()

    stdevs_completed_tasks = list()
    stdevs_ontime_tasks = list()
    stdevs_delayed_tasks = list()
    stdevs_early_tasks = list()

    for i, approach in enumerate(approaches_recovery_method):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        completed_tasks = list()
        ontime_tasks = list()
        delayed_tasks = list()
        early_tasks = list()

        for run_id, run_info in results.get("runs").items():
            print("run_id: ", run_id)
            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
            completed_tasks.append(len(metrics.get("completed_tasks")))
            ontime_tasks.append(len(metrics.get("successful_tasks")))
            delayed_tasks.append(len(metrics.get("delayed_tasks")))
            early_tasks.append(len(metrics.get("early_tasks")))

        if completed_tasks:
            avg_completed_tasks = sum(completed_tasks)/len(completed_tasks)
            stdev_completed_tasks = statistics.stdev(completed_tasks)
        else:
            avg_completed_tasks = 0
            stdev_completed_tasks = 0

        if ontime_tasks:
            avg_ontime_tasks = sum(ontime_tasks)/len(ontime_tasks)
            stdev_ontime_tasks = statistics.stdev(ontime_tasks)
        else:
            avg_ontime_tasks = 0
            stdev_ontime_tasks = 0

        if delayed_tasks:
            avg_delayed_tasks = sum(delayed_tasks)/len(delayed_tasks)
            stdev_delayed_taks = statistics.stdev(delayed_tasks)
        else:
            avg_delayed_tasks = 0
            stdev_delayed_tasks = 0

        if early_tasks:
            avg_early_tasks = sum(early_tasks)/len(early_tasks)
            stdev_early_tasks = statistics.stdev(early_tasks)
        else:
            avg_early_tasks = 0
            stdev_early_tasks = 0

        print("avg completed tasks:", avg_completed_tasks)
        print("avg on time tasks:", avg_ontime_tasks)
        print("avg delayed tasks: ", avg_delayed_tasks)
        print("avg_earliy tasks: ", avg_early_tasks)

        avgs_completed_tasks.append(avg_completed_tasks)
        avgs_ontime_tasks.append(avg_ontime_tasks)
        avgs_delayed_tasks.append(avg_delayed_tasks)
        avgs_early_tasks.append(avg_early_tasks)

        stdevs_completed_tasks.append(stdev_completed_tasks)
        stdevs_ontime_tasks.append(stdev_ontime_tasks)
        stdevs_delayed_tasks.append(stdev_delayed_taks)
        stdevs_early_tasks.append(stdev_early_tasks)

    print("avgs completed tasks:", avgs_completed_tasks)
    print("avgs on time tasks:", avgs_ontime_tasks)
    print("avgs delayed tasks: ", avgs_delayed_tasks)
    print("avgs_earliy tasks: ", avgs_early_tasks)

    plt.bar(index, avgs_completed_tasks, bar_width, alpha=opacity, color='blue', label='Completed', yerr=stdevs_completed_tasks)
    plt.bar(index + bar_width, avgs_ontime_tasks, bar_width, alpha=opacity, color='green', label='On-time', yerr=stdevs_ontime_tasks)
    plt.bar(index + 2*bar_width, avgs_delayed_tasks, bar_width, alpha=opacity, color='red', label='Delayed', yerr=stdevs_delayed_tasks)
    plt.bar(index + 3*bar_width, avgs_early_tasks, bar_width, alpha=opacity, color='orange', label='Early', yerr=stdevs_early_tasks)

    # ax.set_title(title)
    ax.set_ylim(0, 25)
    ax.set_ylabel('Number of tasks')
    ax.set_xlabel('Approaches')
    # ax.set_yticks(np.arange(26))

    plt.legend()

    plt.xticks(index + bar_width, ('TeSSI', 'TeSSI-DREA', 'TeSSI-SREA', 'TeSSI-DSC'))
    plt.tight_layout()
    # plt.show()

    save_plot(fig, plot_name, save_in_path)


def box_plot_completed_tasks(experiment_name, recovery_method, approaches, dataset_name, bidding_rule):
    print("Completed tasks")
    title = get_title(experiment_name, recovery_method, dataset_name)
    save_in_path = get_plot_path(experiment_name)
    plot_name = "completed_tasks_" + recovery_method + '_' + dataset_name

    approaches_recovery_method = [a for a in approaches if recovery_method in a]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    completed = list()
    on_time = list()
    delayed = list()
    early = list()

    for i, approach in enumerate(approaches_recovery_method):
        print("Approach: ", approach)
        path_to_results = '../' + experiment_name + '/' + approach + '/' + bidding_rule
        results_per_dataset = get_dataset_results(path_to_results)
        results = results_per_dataset.get(dataset_name)

        completed_tasks = list()
        on_time_tasks = list()
        delayed_tasks = list()
        early_tasks = list()

        n_runs = 0

        for run_id, run_info in results.get("runs").items():
            # Get only the first n runs
            n_runs += 1
            print("Run: ", n_runs)
            if n_runs > max_n_runs:
                break

            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
            completed_tasks.append(len(metrics.get("completed_tasks")))
            on_time_tasks.append(len(metrics.get("successful_tasks")))
            delayed_tasks.append(len(metrics.get("delayed_tasks")))
            early_tasks.append(len(metrics.get("early_tasks")))

        completed += [completed_tasks]
        on_time += [on_time_tasks]
        delayed += [delayed_tasks]
        early += [early_tasks]

    bp1 = ax.boxplot(completed, positions=np.array(range(len(completed)))*5, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#3333ff'), flierprops=get_flierprops('#3333ff'))
    bp2 = ax.boxplot(on_time, positions=np.array(range(len(on_time)))*5+1, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#339933'), flierprops=get_flierprops('#339933'))
    bp3 = ax.boxplot(delayed, positions=np.array(range(len(delayed)))*5+2, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff3333'), flierprops=get_flierprops('#ff3333'))
    bp4 = ax.boxplot(early, positions=np.array(range(len(early)))*5+3, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ffb733'), flierprops=get_flierprops('#ffb733'))

    set_box_color(bp1, '#3333ff')
    set_box_color(bp2, '#339933')
    set_box_color(bp3,  '#ff3333')
    set_box_color(bp4, '#ffb733')

    plt.plot([], c='#3333ff', label='Completed', linewidth=2)
    plt.plot([], c='#339933', label='On-time', linewidth=2)
    plt.plot([], c='#ff3333', label='Delayed', linewidth=2)
    plt.plot([], c='#ffb733', label='Early', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(ticks) * 5, 5), ticks)
    plt.xlim(-1, len(ticks) * 4+3)
    plt.tight_layout()

    plt.vlines(4, ymin=-1, ymax=26, linewidths=1)
    plt.vlines(9, ymin=-1, ymax=26, linewidths=1)
    plt.vlines(14, ymin=-1, ymax=26, linewidths=1)

    # ax.set_title(title)

    ax.set_ylim(-1, 26)
    ax.set_yticks(list(range(0, 26, 5)))
    ax.set_ylabel('Number of tasks')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    save_plot(fig, plot_name, save_in_path, lgd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment_name', type=str, action='store', help='Experiment_name')
    parser.add_argument('recovery_method', type=str, action='store', help='Recovery method',
                        choices=['preempt', 're-allocate'])

    parser.add_argument('--bidding_rule', type=str, action='store', default='completion_time')

    args = parser.parse_args()

    config_params = get_config_params(experiment=args.experiment_name)
    approaches = config_params.get("approaches")
    datasets = config_params.get("datasets")
    dataset_module = config_params.get("dataset_module")

    for dataset in datasets:
        # box_plot_completed_tasks(args.experiment_name, args.recovery_method, approaches, dataset, args.bidding_rule)
        # box_plot_amount_of_delay(args.experiment_name, args.recovery_method, approaches, dataset, args.bidding_rule)
        # box_plot_allocations(args.experiment_name, args.recovery_method, approaches, dataset, args.bidding_rule)
        # box_plot_fleet_time_distribution(args.experiment_name, args.recovery_method, approaches, dataset, args.bidding_rule)
        # box_plot_times(args.experiment_name, args.recovery_method, approaches, dataset, args.bidding_rule)
        box_plot_robot_usage(args.experiment_name, args.recovery_method, approaches, dataset, args.bidding_rule)

        # box_plot_set_distribution(args.experiment_name, args.recovery_method, approaches, dataset, dataset_module, args.bidding_rule)

        # if args.recovery_method == "re-allocate":
        #     a = [a for a in approaches if args.recovery_method in a]
        #     box_plot_re_allocation_info(args.experiment_name, a, dataset, args.bidding_rule)
        #     box_plot_re_allocation_per_task_info(args.experiment_name, a, dataset, args.bidding_rule)
