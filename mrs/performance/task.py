import logging

from fmlib.models.tasks import TaskStatus
from mrs.db.models.performance.task import TaskPerformance
from fmlib.models.tasks import TransportationTask as Task
from pymodm.context_managers import switch_collection


class TaskPerformanceTracker:
    def __init__(self, auctioneer):
        self.auctioneer = auctioneer
        self.logger = logging.getLogger("mrs.performance.task.tracker")

    def update_allocation_metrics(self, task_id, timetable, only_constraints=False):
        task_performance = TaskPerformance.get_task_performance(task_id)
        metrics = self.get_allocation_metrics(task_id, timetable)
        if only_constraints:
            task_performance.update_allocation(travel_time_boundaries=metrics.get("travel_time_boundaries"),
                                               work_time_boundaries=metrics.get("work_time_boundaries"))
        else:
            task_performance.update_allocation(**metrics)
            task_performance.allocated()

    def get_allocation_metrics(self, task_id, timetable):
        time_to_allocate = self.auctioneer.round.get_time_to_allocate()
        n_previously_allocated_tasks = len(timetable.get_tasks()) - 1

        earliest_start_time = timetable.get_r_time(task_id, "start", lower_bound=True)
        earliest_pickup_time = timetable.get_r_time(task_id, "pickup", lower_bound=True)
        latest_pickup_time = timetable.get_r_time(task_id, "pickup", lower_bound=False)
        earliest_delivery_time = timetable.get_r_time(task_id, "delivery", lower_bound=True)
        latest_delivery_time = timetable.get_r_time(task_id, "delivery", lower_bound=False)

        travel_time_boundaries = [earliest_pickup_time - earliest_start_time, latest_pickup_time - earliest_start_time]
        work_time_boundaries = [earliest_delivery_time - earliest_pickup_time, latest_delivery_time - earliest_pickup_time]

        return {'time_to_allocate': time_to_allocate,
                'n_previously_allocated_tasks': n_previously_allocated_tasks,
                'travel_time_boundaries': travel_time_boundaries,
                'work_time_boundaries': work_time_boundaries}

    def update_delay(self, task_id, assigned_time, node_type, timetable):
        self.logger.debug("Updating delay of task %s ", task_id)
        task_performance = TaskPerformance.get_task_performance(task_id)
        latest_time = timetable.dispatchable_graph.get_time(task_id, node_type, False)
        if assigned_time > latest_time:
            delay = assigned_time - latest_time
            task_performance.update_delay(delay)

    def update_earliness(self, task_id, assigned_time, node_type, timetable):
        self.logger.debug("Updating delay of task %s ", task_id)
        task_performance = TaskPerformance.get_task_performance(task_id)
        earliest_time = timetable.dispatchable_graph.get_time(task_id, node_type)
        if assigned_time < earliest_time:
            earliness = earliest_time - assigned_time
            task_performance.update_earliness(earliness)

    def update_execution_metrics(self, task):
        self.logger.debug("Updating execution metrics of task %s", task.task_id)
        with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
            task_status = TaskStatus.objects.get({"_id": task.task_id})
            travel_action = task_status.progress.actions[0]
            work_action = task_status.progress.actions[1]
            travel_time = (travel_action.finish_time - travel_action.start_time).total_seconds()
            work_time = (work_action.finish_time - work_action.start_time).total_seconds()

        with switch_collection(Task, Task.Meta.archive_collection):
            task_performance = TaskPerformance.get_task_performance(task.task_id)
            task_performance.update_execution(travel_time, work_time)

    @staticmethod
    def update_re_allocations(task):
        task_performance = TaskPerformance.get_task_performance(task.task_id)
        task_performance.increase_n_re_allocation_attempts()
        task_performance.unallocated()
