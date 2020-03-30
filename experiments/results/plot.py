
import os
from datetime import timedelta

import imageio
from fmlib.db.mongo import MongoStore
from plotly import figure_factory as ff

from experiments.db.models.experiment import Experiment
from mrs.timetable.timetable import Timetable
from mrs.utils.time import to_timestamp

colors_schedule = {'Travel': 'rgb(192, 192, 192)',
                   'Work': 'rgb(0, 128, 255)'}

colors_timepoint_constraints = {'Start': 'rgb(0, 102, 204)',
                                'Pickup': 'rgb(0, 153, 0)',
                                'Delivery': 'rgb(255, 0, 0)'}


def get_gantt_task_constraints(task_id, timepoint_constraints):
    task_constraints = list()
    start = timepoint_constraints.get("start")
    pickup = timepoint_constraints.get("pickup")
    delivery = timepoint_constraints.get("delivery")
    if start:
        task_constraints += [dict(Task=task_id, Start=start.earliest_time, Finish=start.latest_time, Resource='Start')]
    if pickup:
        task_constraints += [dict(Task=task_id, Start=pickup.earliest_time, Finish=pickup.latest_time, Resource='Pickup')]
    if delivery:
        task_constraints += [dict(Task=task_id, Start=delivery.earliest_time, Finish=delivery.latest_time, Resource='Delivery')]
    return task_constraints


def get_gantt_task_d_graph(task_id, timepoint_constraints):
    start = timepoint_constraints.get("start")
    pickup = timepoint_constraints.get("pickup")
    delivery = timepoint_constraints.get("delivery")
    travel_time = list()
    work_time = list()
    if start and pickup:
        travel_time = [dict(Task=task_id, Start=start.earliest_time, Finish=pickup.latest_time, Resource='Travel')]
    if pickup and delivery:
        work_time = [dict(Task=task_id, Start=pickup.earliest_time, Finish=delivery.latest_time, Resource='Work')]
    return travel_time + work_time


def get_gantt_task_schedule(robot, start_time, pickup_time, delivery_time):
    return [
        dict(Task=robot, Start=start_time, Finish=pickup_time, Resource='Travel'),
        dict(Task=robot, Start=pickup_time, Finish=delivery_time, Resource='Work')
    ]


def plot_gantt(title, schedule, colors, group_tasks=False, borders=False, **kwargs):
    directory = kwargs.get('dir', './images')
    index = kwargs.get('index')
    xmin = kwargs.get('xmin')
    xmax = kwargs.get('xmax')

    fig = ff.create_gantt(schedule, title=title, group_tasks=group_tasks, showgrid_x=True,
                          show_colorbar=True, index_col='Resource', colors=colors)
    if borders:
        # Taken from https://community.plotly.com/t/borders-in-gantt-charts/32030
        fig.update_traces(mode='lines', line_color='rgb(229, 236, 246)', selector=dict(fill='toself'))

    if xmin and xmax:
        fig.layout.xaxis.update(range=[xmin, xmax])

    if not os.path.exists(directory):
        os.makedirs(directory)
    if index:
        title += '_' + str(index)
    fig.write_image(directory + '/%s.png' % title)
    fig.show()


def get_gantt_robot_d_graph(timetable):
    gantt_d_graph = list()
    task_ids = timetable.get_tasks()
    for task_id in task_ids:
        timepoint_constraints = dict()
        nodes = timetable.dispatchable_graph.get_task_nodes(task_id)
        for node in nodes:
            constraint = timetable.get_timepoint_constraint(task_id, node.node_type)
            timepoint_constraints[node.node_type] = constraint
        gantt_d_graph += get_gantt_task_d_graph(str(task_id), timepoint_constraints)
    return gantt_d_graph


def get_gantt_tasks_schedule(title, tasks, tasks_performance, **kwargs):
    tasks_schedule = list()
    for p in tasks_performance:
        if p.execution:
            dict_repr = p.to_son().to_dict()
            task_id = dict_repr.get('_id')
            task = [task for task in tasks if task.task_id == task_id].pop()
            robot_id = task.assigned_robots[0]
            tasks_schedule += get_gantt_task_schedule(robot_id, p.execution.start_time,
                                                      p.execution.pickup_time,
                                                      p.execution.delivery_time)
    plot_gantt(title, tasks_schedule, colors_schedule, group_tasks=True, borders=True, **kwargs)


def get_gantt_robots_d_graphs(title, robot_performance, **kwargs):
    robots_d_graphs = list()
    r_earliest_time = float('inf')
    r_latest_time = - float('inf')

    for i, timetable_model in enumerate(robot_performance.timetables):
        dict_repr = timetable_model.to_dict()
        timetable = Timetable.from_dict(dict_repr)
        if not timetable.dispatchable_graph.is_empty():
            ztp = timetable.ztp
            et = timetable.dispatchable_graph.get_earliest_time()
            lt = timetable.dispatchable_graph.get_latest_time()

            if et < r_earliest_time:
                r_earliest_time = et
            if lt > r_latest_time:
                r_latest_time = lt

            robot_d_graph = get_gantt_robot_d_graph(timetable)
            if robot_d_graph:
                robots_d_graphs.append(robot_d_graph)

    earliest_time = to_timestamp(ztp, r_earliest_time).to_datetime() - timedelta(seconds=5)
    latest_time = to_timestamp(ztp, r_latest_time).to_datetime() + timedelta(seconds=5)

    for i, robot_d_graph in enumerate(robots_d_graphs):
        kwargs.update(index=i+1, xmin=earliest_time, xmax=latest_time)
        plot_gantt(title + '_' + robot_performance.robot_id, robot_d_graph, colors_schedule, borders=True, **kwargs)


def get_images(dir):
    file_names = list()

    for item in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, item)) and item.endswith('.png'):
            file_names.append(dir + os.path.join(item))

    file_names.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))

    images = [imageio.imread(file_name) for file_name in file_names]
    return images


def get_gif(dir):
    images = get_images(dir)
    imageio.mimsave(dir + 'test.gif', images, 'GIF', duration=1)


if __name__ == '__main__':
    MongoStore(db_name='ccu_store')

    tasks = Experiment.get_tasks()
    tasks_performance = Experiment.get_tasks_performance()
    robots_performance = Experiment.get_robots_performance()

    get_gantt_tasks_schedule('task_schedules', tasks, tasks_performance)

    for robot_performance in robots_performance:
        if robot_performance.allocated_tasks:
            get_gantt_robots_d_graphs('dgraph', robot_performance,
                                      dir='./robot_d_graphs/%s' % robot_performance.robot_id)

            get_gif('./robot_d_graphs/%s/' % robot_performance.robot_id)
