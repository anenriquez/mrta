import collections
import statistics

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

from experiments.results.plot.utils import get_dataset_results, save_plot, set_box_color, get_meanprops, get_plot_path, \
    ticks, get_flierprops, markers
from mrs.config.params import get_config_params

path_to_robot_results = ['robot_scalability_1', 'robot_scalability_2', 'robot_scalability_3', 'robot_scalability_4',
                         'robot_scalability_5']
xticks = ['#robots=1', '#robots=2', '#robots=3', '#robots=4', '#robots=5']


def plot_allocations(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "allocated_tasks"
    fig = plt.figure(figsize=(9, 6))
    robots = list(range(1, 6))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        avgs_allocations = list()
        stdevs_allocations = list()

        for r in path_to_robot_results:
            path_to_results = '../' + r + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')

            robot_allocations = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                robot_allocations.append(len(metrics.get("allocated_tasks")))

            try:
                avg_allocations = statistics.mean(robot_allocations)
            except statistics.StatisticsError:
                # mean requires at least one data point
                avg_allocations = 0

            try:
                stdev_allocations = statistics.stdev(robot_allocations)
            except statistics.StatisticsError:
                # variance requires at least two data points
                stdev_allocations = 0

            avgs_allocations.append(avg_allocations)
            stdevs_allocations.append(stdev_allocations)

        plt.errorbar(robots, avgs_allocations, stdevs_allocations, marker=markers[i], label=ticks[i])

    plt.xticks(robots)
    # plt.yticks(list(range(0, 26, 5)))
    plt.xlabel("Number of robots")
    plt.ylabel("Number of allocated tasks")
    # plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)
    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_allocations(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "box_allocated_tasks"
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    tessi_allocated_tasks = list()
    tessi_drea_allocated_tasks = list()
    tessi_srea_allocated_tasks = list()
    tessi_dsc_allocated_tasks = list()

    for robot in path_to_robot_results:
        print("Robot: ", robot)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + robot + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            approach_allocated_tasks = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                approach_allocated_tasks.append(len(metrics.get("allocated_tasks")))

            if approach == 'tessi-corrective-re-allocate':
                tessi_allocated_tasks += [approach_allocated_tasks]
            elif approach == 'tessi-srea-preventive-re-schedule-re-allocate':
                tessi_drea_allocated_tasks += [approach_allocated_tasks]
            elif approach == 'tessi-srea-corrective-re-allocate':
                tessi_srea_allocated_tasks += [approach_allocated_tasks]
            elif approach == 'tessi-dsc-corrective-re-allocate':
                tessi_dsc_allocated_tasks += [approach_allocated_tasks]

    bp1 = ax.boxplot(tessi_allocated_tasks, positions=np.array(range(len(tessi_allocated_tasks))) * 5,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_allocated_tasks,
                     positions=np.array(range(len(tessi_drea_allocated_tasks))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_allocated_tasks,
                     positions=np.array(range(len(tessi_srea_allocated_tasks))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_allocated_tasks,
                     positions=np.array(range(len(tessi_dsc_allocated_tasks))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Number of allocated tasks')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)


def plot_re_allocations(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "re_allocations"
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    tessi_re_allocations = list()
    tessi_drea_re_allocations = list()
    tessi_srea_re_allocations = list()
    tessi_dsc_re_allocations = list()

    for robot in path_to_robot_results:
        print("Robot: ", robot)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + robot + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            approach_re_allocations = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                re_allocations = 0
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

                for task_metrics in metrics.get("tasks_performance_metrics"):
                    re_allocations += task_metrics.get("n_re_allocations")

                approach_re_allocations.append(re_allocations)

            if approach == 'tessi-corrective-re-allocate':
                tessi_re_allocations += [approach_re_allocations]
            elif approach == 'tessi-srea-preventive-re-schedule-re-allocate':
                tessi_drea_re_allocations += [approach_re_allocations]
            elif approach == 'tessi-srea-corrective-re-allocate':
                tessi_srea_re_allocations += [approach_re_allocations]
            elif approach == 'tessi-dsc-corrective-re-allocate':
                tessi_dsc_re_allocations += [approach_re_allocations]

    print("tessi: ", tessi_re_allocations)
    print("tessi drea: ", tessi_drea_re_allocations)
    print("tessi srea: ", tessi_srea_re_allocations)
    print("tessi dsc: ", tessi_dsc_re_allocations)

    bp1 = ax.boxplot(tessi_re_allocations, positions=np.array(range(len(tessi_re_allocations))) * 5, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_re_allocations, positions=np.array(range(len(tessi_drea_re_allocations))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_re_allocations, positions=np.array(range(len(tessi_srea_re_allocations))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_re_allocations, positions=np.array(range(len(tessi_dsc_re_allocations))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Number of re-allocations')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)


def plot_re_allocation_attempts(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "re_allocation_attempts"
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    tessi_re_allocation_attempts = list()
    tessi_drea_re_allocation_attempts = list()
    tessi_srea_re_allocation_attempts = list()
    tessi_dsc_re_allocation_attempts = list()

    for robot in path_to_robot_results:
        print("Robot: ", robot)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + robot + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            approach_re_allocations_attempts = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                attempts = 0
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

                for task_metrics in metrics.get("tasks_performance_metrics"):
                    attempts += task_metrics.get("n_re_allocation_attempts")

                approach_re_allocations_attempts.append(attempts)

            if approach == 'tessi-corrective-re-allocate':
                tessi_re_allocation_attempts += [approach_re_allocations_attempts]
            elif approach == 'tessi-srea-preventive-re-schedule-re-allocate':
                tessi_drea_re_allocation_attempts += [approach_re_allocations_attempts]
            elif approach == 'tessi-srea-corrective-re-allocate':
                tessi_srea_re_allocation_attempts += [approach_re_allocations_attempts]
            elif approach == 'tessi-dsc-corrective-re-allocate':
                tessi_dsc_re_allocation_attempts += [approach_re_allocations_attempts]

    print("tessi: ", tessi_re_allocation_attempts)
    print("tessi-drea: ", tessi_drea_re_allocation_attempts)
    print("tessi-srea: ", tessi_srea_re_allocation_attempts)
    print("tessi-dsc: ", tessi_dsc_re_allocation_attempts)

    bp1 = ax.boxplot(tessi_re_allocation_attempts, positions=np.array(range(len(tessi_re_allocation_attempts))) * 5, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_re_allocation_attempts, positions=np.array(range(len(tessi_drea_re_allocation_attempts))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_re_allocation_attempts, positions=np.array(range(len(tessi_srea_re_allocation_attempts))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_re_allocation_attempts, positions=np.array(range(len(tessi_dsc_re_allocation_attempts))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Number of re-allocation attempts')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)


def plot_successful_tasks(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "successful_tasks"
    fig = plt.figure(figsize=(9, 6))
    robots = list(range(1, 6))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        avgs_successful_tasks = list()
        stdevs_successful_tasks = list()

        for r in path_to_robot_results:
            path_to_results = '../' + r + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')

            robot_successful_tasks = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                robot_successful_tasks.append(len(metrics.get("successful_tasks")))

            try:
                avg_successful_tasks = statistics.mean(robot_successful_tasks)
            except statistics.StatisticsError:
                # mean requires at least one data point
                avg_successful_tasks = 0

            try:
                stdev_successful_tasks = statistics.stdev(robot_successful_tasks)
            except statistics.StatisticsError:
                # variance requires at least two data points
                stdev_successful_tasks = 0

            avgs_successful_tasks.append(avg_successful_tasks)
            stdevs_successful_tasks.append(stdev_successful_tasks)

        plt.errorbar(robots, avgs_successful_tasks, stdevs_successful_tasks, marker=markers[i], label=ticks[i])

    plt.xticks(robots)
    # plt.yticks(list(range(0, 26, 5)))
    plt.xlabel("Number of robots")
    plt.ylabel("Number of successful tasks")
    # plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)
    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_successful_tasks(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "box_successful_tasks"
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    tessi_successful_tasks = list()
    tessi_drea_successful_tasks = list()
    tessi_srea_successful_tasks = list()
    tessi_dsc_successful_tasks = list()

    for robot in path_to_robot_results:
        print("Robot: ", robot)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + robot + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            approach_successful_tasks = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                approach_successful_tasks.append(len(metrics.get("successful_tasks")))

            if approach == 'tessi-corrective-re-allocate':
                tessi_successful_tasks += [approach_successful_tasks]
            elif approach == 'tessi-srea-preventive-re-schedule-re-allocate':
                tessi_drea_successful_tasks += [approach_successful_tasks]
            elif approach == 'tessi-srea-corrective-re-allocate':
                tessi_srea_successful_tasks += [approach_successful_tasks]
            elif approach == 'tessi-dsc-corrective-re-allocate':
                tessi_dsc_successful_tasks += [approach_successful_tasks]

    bp1 = ax.boxplot(tessi_successful_tasks, positions=np.array(range(len(tessi_successful_tasks))) * 5,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_successful_tasks,
                     positions=np.array(range(len(tessi_drea_successful_tasks))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_successful_tasks,
                     positions=np.array(range(len(tessi_srea_successful_tasks))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_successful_tasks,
                     positions=np.array(range(len(tessi_dsc_successful_tasks))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Number of successful tasks')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)


def box_plot_completed_tasks(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "box_completed_tasks"
    fig = plt.figure(figsize=(9, 6))

    ax = fig.add_subplot(111)

    tessi_completed_tasks = list()
    tessi_drea_completed_tasks = list()
    tessi_srea_completed_tasks = list()
    tessi_dsc_completed_tasks = list()

    for robot in path_to_robot_results:
        print("Robot: ", robot)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + robot + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            approach_completed_tasks = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                approach_completed_tasks.append(len(metrics.get("completed_tasks")))

            if approach == 'tessi-corrective-re-allocate':
                tessi_completed_tasks += [approach_completed_tasks]
            elif approach == 'tessi-srea-preventive-re-schedule-re-allocate':
                tessi_drea_completed_tasks += [approach_completed_tasks]
            elif approach == 'tessi-srea-corrective-re-allocate':
                tessi_srea_completed_tasks += [approach_completed_tasks]
            elif approach == 'tessi-dsc-corrective-re-allocate':
                tessi_dsc_completed_tasks += [approach_completed_tasks]

    bp1 = ax.boxplot(tessi_completed_tasks, positions=np.array(range(len(tessi_completed_tasks))) * 5,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_completed_tasks,
                     positions=np.array(range(len(tessi_drea_completed_tasks))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_completed_tasks,
                     positions=np.array(range(len(tessi_srea_completed_tasks))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_completed_tasks,
                     positions=np.array(range(len(tessi_dsc_completed_tasks))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Number of completed tasks')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)


def plot_completed_tasks(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "completed_tasks"
    fig = plt.figure(figsize=(9, 6))

    robots = list(range(1, 6))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        avgs_completed_tasks = list()
        stdevs_completed_tasks = list()

        for r in path_to_robot_results:
            path_to_results = '../' + r + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')

            robot_completed_tasks = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                robot_completed_tasks.append(len(metrics.get("completed_tasks")))

            try:
                avg_completed_tasks = statistics.mean(robot_completed_tasks)
            except statistics.StatisticsError:
                # mean requires at least one data point
                avg_completed_tasks = 0

            try:
                stdev_completed_tasks = statistics.stdev(robot_completed_tasks)
            except statistics.StatisticsError:
                # variance requires at least two data points
                stdev_completed_tasks = 0

            avgs_completed_tasks.append(avg_completed_tasks)
            stdevs_completed_tasks.append(stdev_completed_tasks)

        plt.errorbar(robots, avgs_completed_tasks, stdevs_completed_tasks, marker=markers[i], label=ticks[i])

    plt.xticks(robots)
    # plt.yticks(list(range(0, 26, 5)))
    plt.xlabel("Number of robots")
    plt.ylabel("Number of completed tasks")
    # plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()

    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_allocation_times(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "allocation_times"
    fig = plt.figure(figsize=(9, 6))

    robots = list(range(1, 6))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        avgs_allocation_times = list()
        stdevs_allocation_times = list()

        for r in path_to_robot_results:
            path_to_results = '../' + r + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            print("robots: ", r)

            robot_allocation_times = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                allocation_time = 0

                for task_performance in metrics.get("tasks_performance_metrics"):
                    allocation_time += task_performance.get('allocation_time')

                robot_allocation_times.append(allocation_time)
                print("allocation time: ", allocation_time)

            try:
                avg_allocation_times = statistics.mean(robot_allocation_times)
            except statistics.StatisticsError:
                # mean requires at least one data point
                avg_allocation_times = 0

            try:
                stdev_allocation_times = statistics.stdev(robot_allocation_times)
            except statistics.StatisticsError:
                # variance requires at least two data points
                stdev_allocation_times = 0

            avgs_allocation_times.append(avg_allocation_times)
            stdevs_allocation_times.append(stdev_allocation_times)

        plt.errorbar(robots, avgs_allocation_times, stdevs_allocation_times, marker=markers[i], label=ticks[i])

    plt.xticks(robots)
    plt.xlabel("Number of robots")
    plt.ylabel("Allocation time (s)")
    # plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_dgraph_recomputation_times(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "dgraph_recomputation_times"
    fig = plt.figure(figsize=(9, 6))

    robots = list(range(1, 6))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        avgs_dgraph_re_computation_times = list()
        stdevs_dgraph_re_computation_times = list()

        for r in path_to_robot_results:
            path_to_results = '../' + r + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            robot_re_computation_times = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                dgraph_re_computation_time = 0

                for robot_performance in metrics.get("robots_performance_metrics"):
                    dgraph_re_computation_time += robot_performance.get("dgraph_recomputation_time")

                robot_re_computation_times.append(dgraph_re_computation_time)

            try:
                avg_recomputation_times = statistics.mean(robot_re_computation_times)
            except statistics.StatisticsError:
                # mean requires at least one data point
                avg_recomputation_times = 0

            try:
                stdev_recomputation_times = statistics.stdev(robot_re_computation_times)
            except statistics.StatisticsError:
                # variance requires at least two data points
                stdev_recomputation_times = 0

            avgs_dgraph_re_computation_times.append(avg_recomputation_times)
            stdevs_dgraph_re_computation_times.append(stdev_recomputation_times)

        plt.errorbar(robots, avgs_dgraph_re_computation_times, stdevs_dgraph_re_computation_times, marker=markers[i], label=ticks[i])

    plt.xticks(robots)
    plt.xlabel("Number of robots")
    plt.ylabel("DGraph re-computation time (s)")
    # plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_re_allocation_times(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "re_allocation_times_"
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    tessi_re_allocation_times = list()
    tessi_drea_re_allocation_times = list()
    tessi_srea_re_allocation_times = list()
    tessi_dsc_re_allocation_times = list()

    for robot in path_to_robot_results:
        print("Robot: ", robot)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + robot + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            approach_re_allocations_times = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                re_allocation_time = 0

                for task_performance in metrics.get("tasks_performance_metrics"):
                    re_allocation_time += task_performance.get('re_allocation_time')

                approach_re_allocations_times.append(re_allocation_time)

            if approach == 'tessi-corrective-re-allocate':
                tessi_re_allocation_times += [approach_re_allocations_times]
            elif approach == 'tessi-srea-preventive-re-schedule-re-allocate':
                tessi_drea_re_allocation_times += [approach_re_allocations_times]
            elif approach == 'tessi-srea-corrective-re-allocate':
                tessi_srea_re_allocation_times += [approach_re_allocations_times]
            elif approach == 'tessi-dsc-corrective-re-allocate':
                tessi_dsc_re_allocation_times += [approach_re_allocations_times]

    bp1 = ax.boxplot(tessi_re_allocation_times, positions=np.array(range(len(tessi_re_allocation_times))) * 5,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_re_allocation_times,
                     positions=np.array(range(len(tessi_drea_re_allocation_times))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_re_allocation_times,
                     positions=np.array(range(len(tessi_srea_re_allocation_times))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_re_allocation_times,
                     positions=np.array(range(len(tessi_dsc_re_allocation_times))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Re-allocation time (s)')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)


def plot_robot_utilization(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    for r in path_to_robot_results:
        save_in_path = get_plot_path('robot_scalability')
        plot_name = "robot_utilization_" + r
        fig = plt.figure(figsize=(9, 6))
        ax = fig.add_subplot(111)
        print("Robot: ", r)
        usage_robot_1 = list()
        usage_robot_2 = list()
        usage_robot_3 = list()
        usage_robot_4 = list()
        usage_robot_5 = list()

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + r + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')

            approach_usage_robot_1 = list()
            approach_usage_robot_2 = list()
            approach_usage_robot_3 = list()
            approach_usage_robot_4 = list()
            approach_usage_robot_5 = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
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

        print("Usage robot 1: ", usage_robot_1)
        print("Usage robot 2: ", usage_robot_2)
        print("Usage robot 3: ", usage_robot_3)
        print("Usage robot 4: ", usage_robot_4)
        print("Usage robot 5: ", usage_robot_5)

        bp1 = ax.boxplot(usage_robot_1, positions=np.array(range(len(usage_robot_1))) * 6, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#3182bd'),
                         flierprops=get_flierprops('#3182bd'))
        bp2 = ax.boxplot(usage_robot_2, positions=np.array(range(len(usage_robot_2))) * 6 + 1, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#2ca25f'),
                         flierprops=get_flierprops('#2ca25f'))
        bp3 = ax.boxplot(usage_robot_3, positions=np.array(range(len(usage_robot_3))) * 6 + 2, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#f03b20'),
                         flierprops=get_flierprops('#f03b20'))
        bp4 = ax.boxplot(usage_robot_4, positions=np.array(range(len(usage_robot_4))) * 6 + 3, widths=0.6,
                         meanline=False, showmeans=True, meanprops=get_meanprops('#756bb1'),
                         flierprops=get_flierprops('#756bb1'))
        bp5 = ax.boxplot(usage_robot_5, positions=np.array(range(len(usage_robot_5))) * 6 + 4, widths=0.6,
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

        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        ymin, ymax = ax.get_ylim()
        plt.vlines(5, ymin=ymin, ymax=ymax, linewidths=1)
        plt.vlines(11, ymin=ymin, ymax=ymax, linewidths=1)
        plt.vlines(17, ymin=ymin, ymax=ymax, linewidths=1)
        plt.ylim(ymin, ymax)

        ax.set_ylabel("Percentage of completed tasks(%)")
        # ax.set_title(title)
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


def plot_bid_time_vs_tasks_in_schedule(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    for r in path_to_robot_results:
        save_in_path = get_plot_path('robot_scalability')
        plot_name = "bid_times_" + r
        fig = plt.figure(figsize=(9, 6))
        print("Robot: ", r)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + r + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')

            bid_times = dict()
            stdev_bid_times = dict()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

                for n_tasks, time_to_bid in metrics.get("bid_times").items():
                    if n_tasks not in bid_times:
                        bid_times[n_tasks] = list()
                    bid_times[n_tasks].append(time_to_bid)

            for n_tasks, times_to_bid in bid_times.items():
                bid_times[n_tasks] = statistics.mean(times_to_bid)
                try:
                    stdev_bid_times[n_tasks] = statistics.stdev(times_to_bid)
                except statistics.StatisticsError:
                    # variance requires at least two data points
                    stdev_bid_times[n_tasks] = 0

            bid_times = collections.OrderedDict(sorted(bid_times.items()))
            stdev_bid_times = collections.OrderedDict(sorted(stdev_bid_times.items()))
            n_tasks_in_schedule = list(bid_times.keys())

            print("n tasks in schedule: ", n_tasks_in_schedule)
            print("bid times: ", bid_times)
            print("Stdev bid times: ", stdev_bid_times)

            plt.errorbar(n_tasks_in_schedule, list(bid_times.values()), list(stdev_bid_times.values()),
                         marker=markers[i], label=ticks[i])

        plt.xlabel("Number of tasks in schedule")
        plt.ylabel("Allocation time (s)")
        # plt.title(title)
        axes = plt.gca()
        axes.yaxis.grid()
        axes.xaxis.set_major_locator(MaxNLocator(integer=True))

        lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

        save_plot(fig, plot_name, save_in_path, lgd)


def plot_re_allocation_per_task_info(approaches):
    title = "Experiment: Robot scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('robot_scalability')
    plot_name = "re_allocation_metrics_per_task"
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    tessi_re_allocations = list()
    tessi_drea_re_allocations = list()
    tessi_srea_re_allocations = list()
    tessi_dsc_re_allocations = list()

    for robot in path_to_robot_results:
        print("Robot: ", robot)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + robot + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            approach_n_re_allocations_per_task = list()

            for run_id, run_info in results.get("runs").items():
                print("Run id: ", run_id)
                n_re_allocations = 0
                n_tasks = 0

                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

                for task_metrics in metrics.get("tasks_performance_metrics"):
                    if task_metrics.get("n_re_allocations") > 0:
                        n_tasks += 1
                        n_re_allocations += task_metrics.get("n_re_allocations")

                if n_tasks > 0:
                    print("n_tasks: ", n_tasks)
                    print("n_re_allocations: ", n_re_allocations)
                    approach_n_re_allocations_per_task.append(n_re_allocations/n_tasks)

            if approach == 'tessi-corrective-re-allocate':
                tessi_re_allocations += [approach_n_re_allocations_per_task]

            elif approach == 'tessi-srea-preventive-re-schedule-re-allocate':
                tessi_drea_re_allocations += [approach_n_re_allocations_per_task]

            elif approach == 'tessi-srea-corrective-re-allocate':
                tessi_srea_re_allocations += [approach_n_re_allocations_per_task]

            elif approach == 'tessi-dsc-corrective-re-allocate':
                tessi_dsc_re_allocations += [approach_n_re_allocations_per_task]

    print("tessi: ", tessi_re_allocations)
    print("tessi-drea: ", tessi_drea_re_allocations)
    print("tessi-srea: ", tessi_srea_re_allocations)
    print("tessi dsc: ", tessi_dsc_re_allocations)

    print(len(tessi_re_allocations))
    print(len(tessi_drea_re_allocations))
    print(len(tessi_srea_re_allocations))
    print(len(tessi_dsc_re_allocations))

    bp1 = ax.boxplot(tessi_re_allocations, positions=np.array(range(len(tessi_re_allocations))) * 5, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_re_allocations, positions=np.array(range(len(tessi_drea_re_allocations))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_re_allocations, positions=np.array(range(len(tessi_srea_re_allocations))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_re_allocations, positions=np.array(range(len(tessi_dsc_re_allocations))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Number of re-allocations per task')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)


def plot_amount_of_delay_and_earliness(approaches):
    save_in_path = get_plot_path('robot_scalability')

    tessi_delay = list()
    tessi_drea_delay = list()
    tessi_srea_delay = list()
    tessi_dsc_delay = list()

    tessi_earliness = list()
    tessi_drea_earliness = list()
    tessi_srea_earliness = list()
    tessi_dsc_earliness = list()

    for robot in path_to_robot_results:
        print("Robot: ", robot)

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../' + robot + '/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            results = results_per_dataset.pop('nonoverlapping_random_25_1')
            approach_n_re_allocations_per_task = list()

            delay = list()
            earliness = list()

            for run_id, run_info in results.get("runs").items():
                print("Run id: ", run_id)

                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                delay.append(metrics.get("delay"))
                earliness.append(metrics.get("earliness"))

            if approach == 'tessi-corrective-re-allocate':
                tessi_delay += [delay]
                tessi_earliness += [earliness]

            elif approach == 'tessi-srea-preventive-re-schedule-re-allocate':
                tessi_drea_delay += [delay]
                tessi_drea_earliness += [earliness]

            elif approach == 'tessi-srea-corrective-re-allocate':
                tessi_srea_delay += [delay]
                tessi_srea_earliness += [earliness]

            elif approach == 'tessi-dsc-corrective-re-allocate':
                tessi_dsc_delay += [delay]
                tessi_dsc_earliness += [earliness]

    print("tessi: ", tessi_delay)
    print("tessi-drea: ", tessi_drea_delay)
    print("tessi-srea: ", tessi_srea_delay)
    print("tessi dsc: ", tessi_dsc_delay)

    plot_name = "delay"
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    bp1 = ax.boxplot(tessi_delay, positions=np.array(range(len(tessi_delay))) * 5, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_delay, positions=np.array(range(len(tessi_drea_delay))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_delay, positions=np.array(range(len(tessi_srea_delay))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_delay, positions=np.array(range(len(tessi_dsc_delay))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Total delay [s]')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)

    plot_name = "earliness"
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    bp1 = ax.boxplot(tessi_earliness, positions=np.array(range(len(tessi_earliness))) * 5, widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#1f77b4'),
                     flierprops=get_flierprops('#1f77b4'))
    bp2 = ax.boxplot(tessi_drea_earliness, positions=np.array(range(len(tessi_drea_earliness))) * 5 + 1,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#ff7f0e'),
                     flierprops=get_flierprops('#ff7f0e'))
    bp3 = ax.boxplot(tessi_srea_earliness, positions=np.array(range(len(tessi_srea_earliness))) * 5 + 2,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#2ca02c'),
                     flierprops=get_flierprops('#2ca02c'))
    bp4 = ax.boxplot(tessi_dsc_earliness, positions=np.array(range(len(tessi_dsc_earliness))) * 5 + 3,
                     widths=0.6,
                     meanline=False, showmeans=True, meanprops=get_meanprops('#d62728'),
                     flierprops=get_flierprops('#d62728'))

    set_box_color(bp1, '#1f77b4')
    set_box_color(bp2, '#ff7f0e')
    set_box_color(bp3, '#2ca02c')
    set_box_color(bp4, '#d62728')

    plt.plot([], c='#1f77b4', label='TeSSI', linewidth=2)
    plt.plot([], c='#ff7f0e', label='TeSSI-DREA', linewidth=2)
    plt.plot([], c='#2ca02c', label='TeSSI-SREA', linewidth=2)
    plt.plot([], c='#d62728', label='TeSSI-DSC', linewidth=2)
    lgd = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    plt.xticks(range(1, len(xticks) * 5, 5), xticks)
    plt.xlim(-1, len(xticks) * 4 + 4)

    ymin, ymax = ax.get_ylim()
    plt.vlines(4, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(9, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(14, ymin=ymin, ymax=ymax, linewidths=1)
    plt.vlines(19, ymin=ymin, ymax=ymax, linewidths=1)
    plt.ylim(ymin, ymax)

    # ax.set_title(title)

    ax.set_ylabel('Total earliness [s]')
    ax.yaxis.grid()

    plt.tick_params(
        axis='x',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        top=False)  # ticks along the top edge are off

    plt.tight_layout()
    save_plot(fig, plot_name, save_in_path, lgd)


if __name__ == '__main__':
    config_params = get_config_params(experiment='robot_scalability_1')
    approaches = config_params.get("approaches")

    box_plot_allocations(approaches)
    box_plot_completed_tasks(approaches)
    box_plot_successful_tasks(approaches)

    plot_allocations(approaches)
    plot_completed_tasks(approaches)
    plot_successful_tasks(approaches)

    plot_amount_of_delay_and_earliness(approaches)

    plot_re_allocations(approaches)
    plot_re_allocation_attempts(approaches)
    plot_re_allocation_times(approaches)

    plot_allocation_times(approaches)
    plot_dgraph_recomputation_times(approaches)
    plot_robot_utilization(approaches)
    plot_bid_time_vs_tasks_in_schedule(approaches)

    plot_re_allocation_per_task_info(approaches)
