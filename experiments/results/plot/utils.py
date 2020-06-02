import os
from mrs.utils.utils import load_yaml_file
import matplotlib.pyplot as plt


ticks = ['TeSSI', 'TeSSI-DREA', 'TeSSI-SREA', 'TeSSI-DSC']
markers = ['^', '8', 's', 'd']
max_n_runs = 15
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']


def get_title(experiment_name, recovery_method, dataset_name):
    title = "Experiment: " + experiment_name + '\n' + \
            "Recovery method: " + recovery_method + '\n' + \
            "Dataset: " + dataset_name
    return title


def get_plot_path(experiment_name):
    return '../' + experiment_name + '/plots/'


def get_dataset_results(path_to_results):
    results = dict()
    for results_file in os.listdir(path_to_results):
        if results_file.endswith('.yaml'):
            r = load_yaml_file(path_to_results + '/' + results_file)
            dataset_name = r.get("dataset_name")
            results[dataset_name] = r
    return results


def save_plot(fig, file_name, save_in_path, lgd):
    print("saving plot: ", file_name)
    print("path: ", save_in_path)
    if not os.path.exists(save_in_path):
        os.makedirs(save_in_path)
    fig.savefig(save_in_path + file_name + '.png', bbox_extra_artists=(lgd,), bbox_inches='tight')


def set_box_color(bp, color):
    # Taken from: https://stackoverflow.com/questions/16592222/matplotlib-group-boxplots
    plt.setp(bp['boxes'], color=color, linewidth=2)
    plt.setp(bp['whiskers'], color=color, linewidth=2)
    plt.setp(bp['caps'], color=color, linewidth=2)
    # plt.setp(bp['fliers'], color=color, linewidth=2)
    plt.setp(bp['medians'], color=color, linewidth=2)


def get_meanprops(color):
    return dict(marker='D', markeredgecolor=color, markerfacecolor=color)


def get_flierprops(color):
    return dict(marker='o', markeredgecolor=color, linewidth=2)
