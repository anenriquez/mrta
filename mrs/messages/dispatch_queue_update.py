from ropod.structs.status import TaskStatus as TaskStatusConst

from mrs.db.models.task import Task
from mrs.utils.as_dict import AsDictMixin


class DispatchQueueUpdate(AsDictMixin):
    n_tasks = 3

    def __init__(self, zero_timepoint, stn, dispatchable_graph, **kwargs):
        self.zero_timepoint = zero_timepoint
        self.stn = stn
        self.dispatchable_graph = dispatchable_graph

    def update_timetable(self, timetable, replace=False):
        stn_cls = timetable.stp_solver.get_stn()
        stn = stn_cls.from_dict(self.stn)
        dispatchable_graph = stn_cls.from_dict(self.dispatchable_graph)
        timetable.zero_timepoint = self.zero_timepoint
        if replace:
            timetable.stn = stn
            timetable.dispatchable_graph = dispatchable_graph
        else:
            merged_stn = self.merge_temporal_graph(timetable.stn, stn)
            merged_dispatchable_graph = self.merge_temporal_graph(timetable.dispatchable_graph, dispatchable_graph)
            timetable.stn = merged_stn
            timetable.dispatchable_graph = merged_dispatchable_graph

        timetable.store()

    @staticmethod
    def merge_temporal_graph(previous_graph, new_graph):
        tasks = list()
        new_task_ids = new_graph.get_tasks()

        scheduled_tasks = [task.task_id for task in Task.get_tasks_by_status(TaskStatusConst.SCHEDULED) if task]
        ongoing_tasks = [task.task_id for task in Task.get_tasks_by_status(TaskStatusConst.ONGOING) if task]

        for i, task_id in enumerate(new_task_ids):
            if task_id in scheduled_tasks or task_id in ongoing_tasks:
                # Keep current version of task
                tasks.append(previous_graph.get_task_graph(task_id))
            else:
                # Use new version of task
                tasks.append(new_graph.get_task_graph(task_id))

        # Get type of previous graph
        merged_graph = previous_graph.__class__()

        for task_graph in tasks:
            merged_graph.add_nodes_from(task_graph.nodes(data=True))
            merged_graph.add_edges_from(task_graph.edges(data=True))

        for i in merged_graph.nodes():
            if i != 0 and merged_graph.has_node(i+1) and not merged_graph.has_edge(i, i + 1):
                merged_graph.add_constraint(i, i + 1)

        return merged_graph

    @property
    def meta_model(self):
        return "dispatch-queue-update"
