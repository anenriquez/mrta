import logging

from fmlib.models.tasks import TaskStatus
from mrs.db.models.performance.task import TaskPerformance
from fmlib.models.tasks import TransportationTask as Task
from pymodm.context_managers import switch_collection


class TaskPerformanceTracker:
    def __init__(self):
        self.logger = logging.getLogger("mrs.performance.task.tracker")

    def update_allocation_metrics(self, task_id, timetable, allocation_time, only_constraints=False):
        task_performance = TaskPerformance.get_task_performance(task_id)
        metrics = self.get_allocation_metrics(task_id, timetable, allocation_time)
        if only_constraints:
            task_performance.update_allocation(start_time=metrics.get("start_time"),
                                               pickup_time=metrics.get("pickup_time"),
                                               delivery_time=metrics.get("delivery_time"))
        else:
            task_performance.update_allocation(**metrics)
            task_performance.allocated()

    def get_allocation_metrics(self, task_id, timetable, allocation_time):
        time_to_allocate = allocation_time
        n_previously_allocated_tasks = len(timetable.get_tasks()) - 1

        start_time = timetable.get_timepoint_constraint(task_id, "start")
        pickup_time = timetable.get_timepoint_constraint(task_id, "pickup")
        delivery_time = timetable.get_timepoint_constraint(task_id, "delivery")

        return {'time_to_allocate': time_to_allocate,
                'n_previously_allocated_tasks': n_previously_allocated_tasks,
                'start_time': start_time,
                'pickup_time': pickup_time,
                'delivery_time': delivery_time}

    def update_scheduling_metrics(self, task_id, timetable):
        self.logger.debug("Updating scheduling metrics of task %s ", task_id)
        task_performance = TaskPerformance.get_task_performance(task_id)
        nodes = timetable.dispatchable_graph.get_task_nodes(task_id)
        for node in nodes:
            constraint = timetable.get_timepoint_constraint(task_id, node.node_type)
            kwargs = {node.node_type + '_time': constraint}
            task_performance.update_scheduling(**kwargs)

    def update_delay(self, task_id, assigned_time, node_id, timetable):
        self.logger.debug("Updating delay of task %s ", task_id)
        task_performance = TaskPerformance.get_task_performance(task_id)
        latest_time = timetable.dispatchable_graph.get_node_latest_time(node_id)
        if assigned_time > latest_time:
            delay = assigned_time - latest_time
            task_performance.update_delay(delay)

    def update_earliness(self, task_id, assigned_time, node_id, timetable):
        self.logger.debug("Updating delay of task %s ", task_id)
        task_performance = TaskPerformance.get_task_performance(task_id)
        earliest_time = timetable.dispatchable_graph.get_node_earliest_time(node_id)
        if assigned_time < earliest_time:
            earliness = earliest_time - assigned_time
            task_performance.update_earliness(earliness)

    def update_execution_metrics(self, task):
        self.logger.debug("Updating execution metrics of task %s", task.task_id)
        with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
            task_status = TaskStatus.objects.get({"_id": task.task_id})
            travel_action = task_status.progress.actions[0]
            work_action = task_status.progress.actions[1]
            start_time = travel_action.start_time
            pickup_time = work_action.start_time
            delivery_time = work_action.finish_time

        with switch_collection(Task, Task.Meta.archive_collection):
            task_performance = TaskPerformance.get_task_performance(task.task_id)
            task_performance.update_execution(start_time, pickup_time, delivery_time)

    @staticmethod
    def update_re_allocations(task):
        task_performance = TaskPerformance.get_task_performance(task.task_id)
        task_performance.increase_n_re_allocation_attempts()
        task_performance.unallocated()
