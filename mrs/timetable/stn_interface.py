import uuid

from fmlib.models.tasks import TransportationTask as Task
from ropod.structs.status import TaskStatus as TaskStatusConst
from stn.task import Edge
from stn.task import Task as STNTask
from stn.task import Timepoint

from mrs.utils.time import relative_to_ztp, to_timestamp


class STNInterface:
    def __init__(self, ztp, stn, dispatchable_graph):
        self.ztp = ztp
        self.stn = stn
        self.dispatchable_graph = dispatchable_graph
        self.stn_tasks = dict()

    def get_stn_task(self, task_id):
        if isinstance(task_id, uuid.UUID):
            task_id = str(task_id)
        return self.stn_tasks.get(task_id)

    def add_stn_task(self, stn_task):
        self.stn_tasks[str(stn_task.task_id)] = stn_task

    def insert_task(self, stn_task, insertion_point):
        self.stn.add_task(stn_task, insertion_point)

    def update_task(self, stn_task):
        self.stn.update_task(stn_task)

    def to_stn_task(self, task, travel_duration, insertion_point, earliest_admissible_time):
        travel_edge = Edge(name="travel_time", mean=travel_duration.mean, variance=travel_duration.variance)
        duration_edge = Edge(name="work_time", mean=task.duration.mean, variance=task.duration.variance)

        pickup_timepoint = self.get_pickup_timepoint(task, travel_edge, insertion_point)
        start_timepoint = self.get_start_timepoint(pickup_timepoint, travel_edge, insertion_point, earliest_admissible_time)
        delivery_timepoint = self.get_delivery_timepoint(pickup_timepoint, duration_edge)

        edges = [travel_edge, duration_edge]
        timepoints = [start_timepoint, pickup_timepoint, delivery_timepoint]
        pickup_action_id = task.plan[0].actions[0].action_id
        delivery_action_id = task.plan[0].actions[-1].action_id

        stn_task = STNTask(task.task_id, timepoints, edges, pickup_action_id, delivery_action_id)
        return stn_task

    def update_stn_task(self, stn_task, travel_duration, insertion_point, earliest_admissible_time):
        travel_edge = Edge(name="travel_time", mean=travel_duration.mean, variance=travel_duration.variance)
        pickup_timepoint = stn_task.get_timepoint("pickup")
        start_timepoint = self.get_start_timepoint(pickup_timepoint, travel_edge, insertion_point, earliest_admissible_time)
        stn_task.update_timepoint("start", start_timepoint.r_earliest_time, start_timepoint.r_latest_time)
        return stn_task

    def get_start_timepoint(self, pickup_timepoint, travel_edge, insertion_point, earliest_admissible_time):
        start_timepoint = self.stn.get_prev_timepoint("start", pickup_timepoint, travel_edge)

        if insertion_point == 1:
            r_earliest_admissible_time = relative_to_ztp(self.ztp, earliest_admissible_time.to_datetime())
            start_timepoint.r_earliest_time = max(r_earliest_admissible_time, start_timepoint.r_earliest_time)

        if insertion_point > 1 and self.previous_task_is_frozen(insertion_point):
            r_latest_delivery_time_previous_task = self.get_r_time_previous_task(insertion_point, "delivery", earliest=False)
            start_timepoint.r_earliest_time = max(start_timepoint.r_earliest_time, r_latest_delivery_time_previous_task)
        return start_timepoint

    def get_pickup_timepoint(self, task, travel_edge, insertion_point):
        r_earliest_pickup_time = relative_to_ztp(self.ztp, task.pickup_constraint.earliest_time)
        r_latest_pickup_time = relative_to_ztp(self.ztp, task.pickup_constraint.latest_time)

        if not task.hard_constraints and insertion_point > 1:
            pickup_time_window = task.pickup_constraint.latest_time - task.pickup_constraint.earliest_time
            r_earliest_delivery_time_previous_task = self.get_r_time_previous_task(insertion_point, "delivery")

            r_earliest_pickup_time = r_earliest_delivery_time_previous_task + travel_edge.mean
            r_latest_pickup_time = r_earliest_pickup_time + pickup_time_window.total_seconds()

            earliest_pickup_time = to_timestamp(self.ztp, r_earliest_pickup_time).to_datetime()
            latest_pickup_time = to_timestamp(self.ztp, r_latest_pickup_time).to_datetime()

            task.update_pickup_constraint(earliest_pickup_time, latest_pickup_time)

        pickup_timepoint = Timepoint(name="pickup", r_earliest_time=r_earliest_pickup_time,
                                     r_latest_time=r_latest_pickup_time)
        return pickup_timepoint

    def get_delivery_timepoint(self, pickup_timepoint, duration_edge):
        delivery_timepoint = self.stn.get_next_timepoint("delivery", pickup_timepoint, duration_edge)
        return delivery_timepoint

    def previous_task_is_frozen(self, insertion_point):
        task_id = self.stn.get_task_id(insertion_point-1)
        previous_task = Task.get_task(task_id)
        if previous_task.status.status in [TaskStatusConst.DISPATCHED, TaskStatusConst.ONGOING]:
            return True
        return False

    def get_r_time_previous_task(self, insertion_point, node_type, earliest=True):
        task_id = self.stn.get_task_id(insertion_point-1)
        previous_task = Task.get_task(task_id)
        return self.dispatchable_graph.get_time(previous_task.task_id, node_type, earliest)
