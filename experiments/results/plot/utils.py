import os
from mrs.utils.utils import load_yaml_file
import matplotlib.pyplot as plt

meanprops = dict(marker='D', markeredgecolor='black', markerfacecolor='black')
ticks = ['TeSSI', 'TeSSI-DREA', 'TeSSI-SREA', 'TeSSI-DSC']
markers = ['^', '8', 's', 'd']


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


def save_plot(fig, file_name, save_in_path):
    print("saving plot: ", file_name)
    print("path: ", save_in_path)
    if not os.path.exists(save_in_path):
        os.makedirs(save_in_path)
    fig.savefig(save_in_path + file_name + '.png', bbox_inches='tight')


def set_box_color(bp, color):
    # Taken from: https://stackoverflow.com/questions/16592222/matplotlib-group-boxplots
    plt.setp(bp['boxes'], color=color)
    plt.setp(bp['whiskers'], color=color)
    plt.setp(bp['caps'], color=color)
    plt.setp(bp['fliers'], color=color)
    plt.setp(bp['medians'], color='black')
