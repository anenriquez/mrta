import collections
import statistics

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

from experiments.results.plot.utils import get_dataset_results, save_plot, set_box_color, get_meanprops, get_plot_path, \
    ticks, get_flierprops, markers
from mrs.config.params import get_config_params


def plot_allocations_(approach):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n" +\
            "Approach: " + approach

    save_in_path = get_plot_path('task_scalability')
    plot_name = "allocations_" + approach
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    path_to_results = '../task_scalability/' + approach + '/completion_time'
    results_per_dataset = get_dataset_results(path_to_results)

    avgs_allocated_tasks = list()
    avgs_unallocated_tasks = list()
    avgs_successful_re_allocations = list()

    stdevs_allocated_tasks = list()
    stdevs_unallocated_tasks = list()
    stdevs_successful_re_allocations = list()

    # Order results
    results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}
    ordered_results = collections.OrderedDict(sorted(results.items()))

    print("approach: ", approach)

    for n_tasks, results in ordered_results.items():
        print("n_tasks:", results["n_tasks"])
        dataset_allocated_tasks = list()
        dataset_unallocated_tasks = list()
        dataset_successful_re_allocations = list()

        for run_id, run_info in results.get("runs").items():
            print("run_id: ", run_id)
            metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
            dataset_allocated_tasks.append(len(metrics.get("allocated_tasks")))
            dataset_unallocated_tasks.append(len(metrics.get("unallocated_tasks")))
            dataset_successful_re_allocations.append(len(metrics.get("successful_reallocations")))

        if dataset_allocated_tasks:
            avg_allocated_tasks = sum(dataset_allocated_tasks)/len(dataset_allocated_tasks)
            stdev_allocated_tasks = statistics.stdev(dataset_allocated_tasks)
        else:
            avg_allocated_tasks = 0
            stdev_allocated_tasks = 0

        if dataset_unallocated_tasks:
            avg_unallocated_tasks = sum(dataset_unallocated_tasks)/len(dataset_unallocated_tasks)
            stdev_unallocated_tasks = 0
        else:
            avg_unallocated_tasks = 0
            stdev_unallocated_tasks = 0

        if dataset_successful_re_allocations:
            avg_successful_re_allocations = sum(dataset_successful_re_allocations)/len(dataset_successful_re_allocations)
            stdev_successful_re_allocations = 0
        else:
            avg_successful_re_allocations = 0
            stdev_successful_re_allocations = 0

        avgs_allocated_tasks.append(avg_allocated_tasks)
        avgs_unallocated_tasks.append(avg_unallocated_tasks)
        avgs_successful_re_allocations.append(avg_successful_re_allocations)

        stdevs_allocated_tasks.append(stdev_allocated_tasks)
        stdevs_unallocated_tasks.append(stdev_unallocated_tasks)
        stdevs_successful_re_allocations.append(stdev_successful_re_allocations)

    plt.errorbar(tasks, avgs_allocated_tasks, stdevs_allocated_tasks, label="Allocated", marker='o')
    plt.errorbar(tasks, avgs_unallocated_tasks, stdevs_unallocated_tasks, label="Unallocated", marker='X')
    plt.errorbar(tasks, avgs_successful_re_allocations, stdevs_successful_re_allocations,
                 label="Successful re-allocations", marker='<')

    plt.xticks(tasks)
    plt.yticks(list(range(0, 26, 5)))
    plt.xlabel("Number of  tasks")
    plt.ylabel("Number of tasks")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_allocations(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('task_scalability')
    plot_name = "allocated_tasks"
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../task_scalability/' + approach + '/completion_time'
        results_per_dataset = get_dataset_results(path_to_results)

        for dataset_name, results in results_per_dataset.items():
            print("dataset_name: ", dataset_name)

        avgs_allocated_tasks = list()
        stdevs_allocated_tasks = list()

        # Order results
        results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}

        for n_tasks_, _ in results.items():
            print("n_tasks:", n_tasks_)

        ordered_results = collections.OrderedDict(sorted(results.items()))

        for n_tasks, results in ordered_results.items():
            print("n_tasks:", results["n_tasks"])
            dataset_allocated_tasks = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                dataset_allocated_tasks.append(len(metrics.get("allocated_tasks")))

            if dataset_allocated_tasks:
                avg_allocated_tasks = sum(dataset_allocated_tasks) / len(dataset_allocated_tasks)
                stdev_allocated_tasks = statistics.stdev(dataset_allocated_tasks)
            else:
                avg_allocated_tasks = 0
                stdev_allocated_tasks = 0

            avgs_allocated_tasks.append(avg_allocated_tasks)
            stdevs_allocated_tasks.append(stdev_allocated_tasks)

        plt.errorbar(tasks, avgs_allocated_tasks, stdevs_allocated_tasks, marker=markers[i], label=ticks[i])

    plt.xticks(tasks)
    plt.yticks(list(range(0, 26, 5)))
    plt.xlabel("Number of tasks")
    plt.ylabel("Number of allocated tasks")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_re_allocations(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('task_scalability')
    plot_name = "re_allocations"
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../task_scalability/' + approach + '/completion_time'
        results_per_dataset = get_dataset_results(path_to_results)

        avgs_re_allocations = list()

        stdevs_re_allocations = list()

        # Order results
        results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}
        ordered_results = collections.OrderedDict(sorted(results.items()))

        for n_tasks, results in ordered_results.items():
            print("n_tasks:", results["n_tasks"])
            dataset_re_allocations = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                successful_reallocations = len(metrics.get("successful_reallocations"))
                dataset_re_allocations.append(successful_reallocations)

            if dataset_re_allocations:
                avg_re_allocations = sum(dataset_re_allocations) / len(dataset_re_allocations)
                stdev_re_allocations = statistics.stdev(dataset_re_allocations)
            else:
                avg_re_allocations = 0
                stdev_re_allocations = 0

            avgs_re_allocations.append(avg_re_allocations)
            stdevs_re_allocations.append(stdev_re_allocations)

        plt.errorbar(tasks, avgs_re_allocations, stdevs_re_allocations, marker=markers[i], label=ticks[i])

    plt.xticks(tasks)
    plt.xlabel("Number of tasks")
    plt.ylabel("Number of re-allocated tasks")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    axes.yaxis.set_major_locator(MaxNLocator(integer=True))

    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_re_allocation_attempts(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('task_scalability')
    plot_name = "re_allocation_attempts"
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../task_scalability/' + approach + '/completion_time'
        results_per_dataset = get_dataset_results(path_to_results)

        avgs_re_allocation_attempts = list()

        stdevs_re_allocation_attempts = list()

        # Order results
        results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}
        ordered_results = collections.OrderedDict(sorted(results.items()))

        for n_tasks, results in ordered_results.items():
            print("n_tasks:", results["n_tasks"])
            dataset_re_allocation_attempts = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

                successful_reallocations = len(metrics.get("successful_reallocations"))
                unsucessful_reallocations = len(metrics.get("unsuccessful_reallocations"))
                attempts = successful_reallocations + unsucessful_reallocations

                dataset_re_allocation_attempts.append(attempts)

            if dataset_re_allocation_attempts:
                avg_re_allocation_attempts = sum(dataset_re_allocation_attempts) / len(dataset_re_allocation_attempts)
                stdev_re_allocation_attempts = statistics.stdev(dataset_re_allocation_attempts)
            else:
                avg_re_allocation_attempts = 0
                stdev_re_allocation_attempts = 0

            avgs_re_allocation_attempts.append(avg_re_allocation_attempts)
            stdevs_re_allocation_attempts.append(stdev_re_allocation_attempts)

        plt.errorbar(tasks, avgs_re_allocation_attempts, stdevs_re_allocation_attempts, marker=markers[i], label=ticks[i])

    plt.xticks(tasks)
    # plt.yticks(list(range(0, 26, 5)))
    plt.xlabel("Number of tasks")
    plt.ylabel("Number of re-allocation attempts")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    axes.yaxis.set_major_locator(MaxNLocator(integer=True))

    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_successful_tasks(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('task_scalability')
    plot_name = "successful_tasks"
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../task_scalability/' + approach + '/completion_time'
        results_per_dataset = get_dataset_results(path_to_results)

        avgs_successful_tasks = list()
        stdevs_successful_tasks = list()

        # Order results
        results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}
        ordered_results = collections.OrderedDict(sorted(results.items()))

        for n_tasks, results in ordered_results.items():
            print("n_tasks:", results["n_tasks"])
            dataset_successful_tasks = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                dataset_successful_tasks.append(len(metrics.get("successful_tasks")))

            if dataset_successful_tasks:
                avg_successful_tasks = sum(dataset_successful_tasks) / len(dataset_successful_tasks)
                stdev_successful_tasks = statistics.stdev(dataset_successful_tasks)
            else:
                avg_successful_tasks = 0
                stdev_successful_tasks = 0

            avgs_successful_tasks.append(avg_successful_tasks)
            stdevs_successful_tasks.append(stdev_successful_tasks)

        plt.errorbar(tasks, avgs_successful_tasks, stdevs_successful_tasks, marker=markers[i], label=ticks[i])

    plt.xticks(tasks)
    plt.yticks(list(range(0, 26, 5)))
    plt.xlabel("Number of tasks")
    plt.ylabel("Number of successful tasks")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()

    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_completed_tasks(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('task_scalability')
    plot_name = "completed_tasks"
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../task_scalability/' + approach + '/completion_time'
        results_per_dataset = get_dataset_results(path_to_results)

        avgs_completed_tasks = list()
        stdevs_completed_tasks = list()

        # Order results
        results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}
        ordered_results = collections.OrderedDict(sorted(results.items()))

        for n_tasks, results in ordered_results.items():
            print("n_tasks:", results["n_tasks"])
            datset_completed_tasks = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                datset_completed_tasks.append(len(metrics.get("completed_tasks")))

            if datset_completed_tasks:
                avg_completed_tasks = sum(datset_completed_tasks) / len(datset_completed_tasks)
                stdev_completed_tasks = statistics.stdev(datset_completed_tasks)
            else:
                avg_completed_tasks = 0
                stdev_completed_tasks = 0

            avgs_completed_tasks.append(avg_completed_tasks)
            stdevs_completed_tasks.append(stdev_completed_tasks)

        plt.errorbar(tasks, avgs_completed_tasks, stdevs_completed_tasks, marker=markers[i], label=ticks[i])

    plt.xticks(tasks)
    plt.yticks(list(range(0, 26, 5)))
    plt.xlabel("Number of tasks")
    plt.ylabel("Number of completed tasks")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()

    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_allocation_times(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('task_scalability')
    plot_name = "allocation_times"
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../task_scalability/' + approach + '/completion_time'
        results_per_dataset = get_dataset_results(path_to_results)

        avgs_allocation_times = list()
        stdevs_allocation_times = list()

        # Order results
        results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}
        ordered_results = collections.OrderedDict(sorted(results.items()))

        for n_tasks, results in ordered_results.items():
            print("n_tasks: ", results["n_tasks"])
            dataset_allocation_times = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                allocation_time = 0

                for task_performance in metrics.get("tasks_performance_metrics"):
                    allocation_time += task_performance.get('allocation_time')

                dataset_allocation_times.append(allocation_time)
                print("allocation time: ", allocation_time)

            if dataset_allocation_times:
                avg_allocation_times = sum(dataset_allocation_times)/len(dataset_allocation_times)
                stdev_allocation_times = statistics.stdev(dataset_allocation_times)
            else:
                avg_allocation_times = 0
                stdev_allocation_times = 0

            avgs_allocation_times.append(avg_allocation_times)
            stdevs_allocation_times.append(stdev_allocation_times)

        print("tasks: ", tasks)
        print("avgs allocation times: ", avgs_allocation_times)
        print("stdevs allocation times: ", stdevs_allocation_times)

        plt.errorbar(tasks, avgs_allocation_times, stdevs_allocation_times, marker=markers[i], label=ticks[i])

    plt.xticks(tasks)
    plt.xlabel("Number of tasks")
    plt.ylabel("Allocation time (s)")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_bid_time_vs_tasks_in_schedule(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    for n_tasks in range(5, 26, 5):
        print("n_tasks: ", n_tasks)

        save_in_path = get_plot_path('task_scalability')
        plot_name = "bid_times_" + str(n_tasks)
        fig = plt.figure(figsize=(9, 6))

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../task_scalability/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            dataset_name = 'overlapping_random_%s_5_1' % str(n_tasks)
            print("Dataset name: ", dataset_name)
            results = results_per_dataset.pop(dataset_name)

            bid_times = dict()
            stdev_bid_times = dict()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

                # if metrics.get("bid_times") is None:
                #     print("No allocation information")
                #     continue

                for n_previously_allocated_tasks, time_to_bid in metrics.get("bid_times").items():
                    if n_previously_allocated_tasks not in bid_times:
                        bid_times[n_previously_allocated_tasks] = list()
                    bid_times[n_previously_allocated_tasks].append(time_to_bid)

            for n_previously_allocated_tasks, times_to_bid in bid_times.items():
                bid_times[n_previously_allocated_tasks] = statistics.mean(times_to_bid)
                try:
                    stdev_bid_times[n_previously_allocated_tasks] = statistics.stdev(times_to_bid)
                except statistics.StatisticsError:
                    # variance requires at least two data points
                    stdev_bid_times[n_previously_allocated_tasks] = 0

            bid_times = collections.OrderedDict(sorted(bid_times.items()))
            stdev_bid_times = collections.OrderedDict(sorted(stdev_bid_times.items()))
            n_tasks_in_schedule = list(bid_times.keys())

            print("n tasks in schedule: ", n_tasks_in_schedule)
            print("bid times: ", bid_times)
            print("Stdev bid times: ", stdev_bid_times)

            plt.errorbar(n_tasks_in_schedule, list(bid_times.values()), list(stdev_bid_times.values()),
                         marker=markers[i], label=ticks[i])

        # plt.xticks(n_tasks_in_schedule)
        plt.xlabel("Number of tasks in schedule")
        plt.ylabel("Bid time (s)")
        plt.title(title)
        axes = plt.gca()
        axes.yaxis.grid()
        lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

        save_plot(fig, plot_name, save_in_path, lgd)


def plot_dgraph_recomputation_times(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('task_scalability')
    plot_name = "dgraph_recomputation_times"
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../task_scalability/' + approach + '/completion_time'
        results_per_dataset = get_dataset_results(path_to_results)

        avgs_dgraph_re_computation_times = list()

        stdevs_dgraph_re_computation_times = list()

        # Order results
        results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}
        ordered_results = collections.OrderedDict(sorted(results.items()))

        for n_tasks, results in ordered_results.items():
            print("n_tasks: ", results["n_tasks"])
            dataset_re_computation_times = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                dgraph_re_computation_time = 0

                for robot_performance in metrics.get("robots_performance_metrics"):
                    dgraph_re_computation_time += robot_performance.get("dgraph_recomputation_time")

                dataset_re_computation_times.append(dgraph_re_computation_time)

            if dataset_re_computation_times:
                avg_recomputation_times = sum(dataset_re_computation_times)/len(dataset_re_computation_times)
                stdev_recomputation_times = statistics.stdev(dataset_re_computation_times)
            else:
                avg_recomputation_times = 0
                stdev_recomputation_times = 0

            avgs_dgraph_re_computation_times.append(avg_recomputation_times)
            stdevs_dgraph_re_computation_times.append(stdev_recomputation_times)

        print("tasks: ", tasks)
        print("avgs recomputation times: ", avgs_dgraph_re_computation_times)
        print("stdevs recomputation times: ", stdevs_dgraph_re_computation_times)

        plt.errorbar(tasks, avgs_dgraph_re_computation_times, stdevs_dgraph_re_computation_times, marker=markers[i], label=ticks[i])

    plt.xticks(tasks)
    plt.xlabel("Number of tasks")
    plt.ylabel("DGraph re-computation time (s)")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_re_allocation_times(approaches):
    title = "Experiment: Task scalability \n" + \
            "Recovery method: re-allocation \n"

    save_in_path = get_plot_path('task_scalability')
    plot_name = "re_allocation_times"
    fig = plt.figure(figsize=(9, 6))

    tasks = list(range(5, 26, 5))

    for i, approach in enumerate(approaches):
        print("Approach: ", approach)
        path_to_results = '../task_scalability/' + approach + '/completion_time'
        results_per_dataset = get_dataset_results(path_to_results)

        avgs_re_allocation_times = list()

        stdevs_re_allocation_times = list()

        # Order results
        results = {r.get('n_tasks'): r for (dataset_name, r) in results_per_dataset.items()}
        ordered_results = collections.OrderedDict(sorted(results.items()))

        for n_tasks, results in ordered_results.items():
            print("n_tasks: ", results["n_tasks"])
            dataset_re_allocation_times = list()

            for run_id, run_info in results.get("runs").items():
                print("run_id: ", run_id)
                metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")
                re_allocation_time = 0

                for task_performance in metrics.get("tasks_performance_metrics"):
                    re_allocation_time += task_performance.get('re_allocation_time')

                dataset_re_allocation_times.append(re_allocation_time)

            print("re-allocation times: ", dataset_re_allocation_times)

            if dataset_re_allocation_times:
                avg_re_allocation_times = sum(dataset_re_allocation_times)/len(dataset_re_allocation_times)
                stdev_re_allocation_times = statistics.stdev(dataset_re_allocation_times)
                print("avg_re_allocation_times: ", avg_re_allocation_times)
                print("stdev_re_allocation_times: ", stdev_re_allocation_times)
            else:
                avg_re_allocation_times = 0
                stdev_re_allocation_times = 0
                print("avg_re_allocation_times: ", avg_re_allocation_times)
                print("stdev_re_allocation_times: ", stdev_re_allocation_times)

            avgs_re_allocation_times.append(avg_re_allocation_times)
            stdevs_re_allocation_times.append(stdev_re_allocation_times)

        print("tasks: ", tasks)
        print("avgs re allocation times: ", avgs_re_allocation_times)
        print("stdevs re allocation times: ", stdevs_re_allocation_times)
        # TODO: Limit lower limit to zero
        lolims = np.ones(5, dtype=bool)

        plt.errorbar(tasks, avgs_re_allocation_times, stdevs_re_allocation_times, marker=markers[i], label=ticks[i])

    plt.xticks(tasks)
    plt.xlabel("Number of tasks")
    plt.ylabel("Re-allocation time (s)")
    plt.title(title)
    axes = plt.gca()
    axes.yaxis.grid()
    lgd = axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, fancybox=True, shadow=True)

    save_plot(fig, plot_name, save_in_path, lgd)


def plot_robot_utilization(approaches):

    for n_tasks in range(5, 26, 5):
        print("n_tasks: ", n_tasks)

        title = "Experiment 3:  %s tasks" % str(n_tasks) + "\n" + \
                "Recovery method: re-allocation \n"

        save_in_path = get_plot_path('task_scalability')
        plot_name = "robot_utilization_" + str(n_tasks)
        fig = plt.figure(figsize=(9, 6))
        ax = fig.add_subplot(111)

        usage_robot_1 = list()
        usage_robot_2 = list()
        usage_robot_3 = list()
        usage_robot_4 = list()
        usage_robot_5 = list()

        for i, approach in enumerate(approaches):
            print("Approach: ", approach)
            path_to_results = '../task_scalability/' + approach + '/completion_time'
            results_per_dataset = get_dataset_results(path_to_results)
            dataset_name = 'overlapping_random_%s_5_1' % str(n_tasks)
            print("Dataset name: ", dataset_name)
            results = results_per_dataset.pop(dataset_name)

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

        ax.set_ylabel("Percentage of completed tasks (%)")
        ax.set_title(title)
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


if __name__ == '__main__':
    config_params = get_config_params(experiment='task_scalability')
    approaches = config_params.get("approaches")

    # plot_allocations(approaches)
    # plot_re_allocations(approaches)
    # plot_re_allocation_attempts(approaches)
    # plot_successful_tasks(approaches)
    # plot_completed_tasks(approaches)
    #
    # plot_allocation_times(approaches)
    # plot_dgraph_recomputation_times(approaches)
    # plot_re_allocation_times(approaches)
    # plot_bid_time_vs_tasks_in_schedule(approaches)

    plot_robot_utilization(approaches)

