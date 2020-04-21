import argparse

import matplotlib.pyplot as plt
from experiments.results.plot.utils import get_dataset_results, save_plot, set_box_color, meanprops
from experiments.results.plot.utils import get_dataset_results, save_plot


def box_plot_robot(results, approach, path_to_results):
    title = "Experiment: " + results.get("name") + '\n' + \
            "Approach: " + approach + '\n' + \
            "Dataset: " + results.get("dataset_name")
    save_in_path = path_to_results + '/plots/'
    plot_name = 'robots_' + results.get("dataset_name")

    # Tasks allocated per robot
    usage_robot_1 = list()
    usage_robot_2 = list()
    usage_robot_3 = list()
    usage_robot_4 = list()
    usage_robot_5 = list()

    # Get usage with respect to the total tasks ?

    for run_id, run_info in results.get("runs").items():
        robot_metrics = run_info.get("performance_metrics").get("fleet_performance_metrics").get("robots_performance_metrics")
        for robot in robot_metrics:
            if robot.get("robot_id") == "robot_001":
                usage_robot_1.append(robot["usage"])
            if robot.get("robot_id") == "robot_002":
                usage_robot_2.append(robot["usage"])
            if robot.get("robot_id") == "robot_003":
                usage_robot_3.append(robot["usage"])
            if robot.get("robot_id") == "robot_004":
                usage_robot_4.append(robot["usage"])
            if robot.get("robot_id") == "robot_005":
                usage_robot_5.append(robot["usage"])

    data_to_plot = [usage_robot_1, usage_robot_2, usage_robot_3, usage_robot_4, usage_robot_5]
    labels = ["Robot 001", "Robot 002", "Robot 003", "Robot 004", "Robot 005"]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)
    colors = ['#3182bd', '#2ca25f', '#f03b20',  '#756bb1', '#7fcdbb']

    bp = ax.boxplot(data_to_plot, patch_artist=True, labels=labels, meanline=False, showmeans=True, meanprops=meanprops)

    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)

    for median in bp['medians']:
        median.set(color='black')

    ax.set_title(title)

    ax.set_ylim(0, 100)
    ax.set_ylabel('Percentage of tasks (%)')

    save_plot(fig, plot_name, save_in_path)


def box_plot_task(results, approach, path_to_results):
    title = "Experiment: " + results.get("name") + '\n' +\
            "Approach: " + approach + '\n' +\
            "Dataset: " + results.get("dataset_name")
    save_in_path = path_to_results + '/plots/'
    plot_name = 'tasks_' + results.get("dataset_name")

    print("title: ", title)
    print("plot name: ", plot_name)

    n_completed_tasks = list()
    n_successful_tasks = list()
    n_unallocated_tasks = list()
    n_preempted_tasks = list()
    n_unsucessful_reallocations_tasks = list()

    for run_id, run_info in results.get("runs").items():
        metrics = run_info.get("performance_metrics").get("fleet_performance_metrics")

        n_completed_tasks.append(len(metrics.get("completed_tasks")))
        n_successful_tasks.append(len(metrics.get("successful_tasks")))
        n_unallocated_tasks.append(len(metrics.get("unallocated_tasks")))
        n_preempted_tasks.append(len(metrics.get("preempted_tasks")))
        n_unsucessful_reallocations_tasks.append(len(metrics.get("unsuccessful_reallocations")))

    # Maybe remove successful tasks

    if "preempt" in path_to_results:
        data_to_plot = [n_completed_tasks, n_successful_tasks, n_unallocated_tasks, n_preempted_tasks]
        labels = ['Completed', 'Successful', 'Unallocated', 'Preempted']

    elif "re-allocate" in path_to_results:
        data_to_plot = [n_completed_tasks, n_successful_tasks, n_unallocated_tasks, n_unsucessful_reallocations_tasks]
        labels = ['Completed', 'Successful', 'Unallocated', 'Unsuccessful re-allocations']
        # colors = ['#72a0f6', '#65d095', '#f0f352', '#fb8870']

    colors = ['#3333ff', '#339933', '#ffb733', '#ff3333']
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    bp = ax.boxplot(data_to_plot, patch_artist=True, labels=labels, meanline=False, showmeans=True, meanprops=meanprops)

    ax.set_title(title)

    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)

    for median in bp['medians']:
        median.set(color='black')

    ax.set_ylim(0, 25)
    ax.set_ylabel('Number of tasks')

    save_plot(fig, plot_name, save_in_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment_name', type=str, action='store', help='Experiment_name')
    parser.add_argument('approach', type=str, action='store', help='Approach name')
    parser.add_argument('--bidding_rule', type=str, action='store', default='completion_time')
    args = parser.parse_args()

    path_to_results_ = '../' + args.experiment_name + '/' + args.approach + '/' + args.bidding_rule

    results = get_dataset_results(path_to_results_)

    for dataset_name, r in results.items():
        box_plot_task(r, args.approach, path_to_results_)
        box_plot_robot(r, args.approach, path_to_results_)