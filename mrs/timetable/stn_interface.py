from fmlib.models.tasks import Task
from fmlib.models.tasks import TimepointConstraint
from stn.task import InterTimepointConstraint as STNInterTimepointConstraint
from stn.task import Task as STNTask
from stn.task import TimepointConstraint as STNTimepointConstraint

from mrs.utils.time import relative_to_ztp, to_timestamp


class STNInterface:
    def __init__(self, ztp, stn, dispatchable_graph):
        self.ztp = ztp
        self.stn = stn
        self.dispatchable_graph = dispatchable_graph
        self.stn_tasks = dict()

    def get_stn_task(self, task_id):
        return self.stn_tasks.get(task_id)

    def add_stn_task(self, stn_task):
        self.stn_tasks[stn_task.task_id] = stn_task

    def insert_task(self, stn_task, insertion_point):
        self.stn.add_task(stn_task, insertion_point)

    def update_task(self, stn_task):
        self.stn.update_task(stn_task)

    def to_stn_task(self, task, insertion_point, earliest_admissible_time):
        self.update_pickup_constraint(task, insertion_point)
        self.update_start_constraint(task, insertion_point, earliest_admissible_time)
        self.update_delivery_constraint(task)
        stn_timepoint_constraints, stn_inter_timepoint_constraints = self.get_constraints(task)
        stn_task = STNTask(task.task_id, stn_timepoint_constraints, stn_inter_timepoint_constraints)
        return stn_task

    def update_stn_task(self, task, insertion_point, earliest_admissible_time):
        self.update_start_constraint(task, insertion_point, earliest_admissible_time)
        stn_timepoint_constraints, stn_inter_timepoint_constraints = self.get_constraints(task)
        stn_task = STNTask(task.task_id, stn_timepoint_constraints, stn_inter_timepoint_constraints)
        return stn_task

    def update_start_constraint(self, task, insertion_point, earliest_admissible_time):
        pickup_constraint = task.get_timepoint_constraint("pickup")
        travel_time = task.get_inter_timepoint_constraint("travel_time")
        r_earliest_time = relative_to_ztp(self.ztp, pickup_constraint.earliest_time)
        r_latest_time = relative_to_ztp(self.ztp, pickup_constraint.latest_time)
        stn_next_constraint = STNTimepointConstraint(name="pickup", r_earliest_time=r_earliest_time, r_latest_time=r_latest_time)
        inter_timepoint_constraint = STNInterTimepointConstraint(**travel_time.to_dict())
        stn_start_constraint = self.stn.get_prev_timepoint_constraint("start", stn_next_constraint, inter_timepoint_constraint)

        if insertion_point == 1:
            r_earliest_admissible_time = earliest_admissible_time.get_difference(self.ztp).total_seconds()
            stn_start_constraint.r_earliest_time = max(r_earliest_admissible_time, stn_start_constraint.r_earliest_time)

        if insertion_point > 1 and self.previous_task_is_frozen(insertion_point):
            r_latest_delivery_time_previous_task = self.get_r_time_previous_task(insertion_point, "delivery", earliest=False)
            stn_start_constraint.r_earliest_time = max(stn_start_constraint.r_earliest_time,
                                                       r_latest_delivery_time_previous_task)

        earliest_time = to_timestamp(self.ztp, stn_start_constraint.r_earliest_time)
        latest_time = to_timestamp(self.ztp, stn_start_constraint.r_latest_time)
        start_constraint = TimepointConstraint(name="start",
                                               earliest_time=earliest_time.to_datetime(),
                                               latest_time=latest_time.to_datetime())

        task.update_timepoint_constraint(**start_constraint.to_dict())

    def update_pickup_constraint(self, task, insertion_point):
        hard_pickup_constraint = task.get_timepoint_constraint("pickup")
        pickup_time_window = hard_pickup_constraint.latest_time - hard_pickup_constraint.earliest_time

        if not task.constraints.hard and insertion_point > 1:
            r_earliest_delivery_time_previous_task = self.get_r_time_previous_task(insertion_point, "delivery")
            travel_time = task.get_inter_timepoint_constraint("travel_time")

            r_earliest_pickup_time = r_earliest_delivery_time_previous_task + travel_time.mean
            r_latest_pickup_time = r_earliest_pickup_time + pickup_time_window.total_seconds()

            earliest_pickup_time = to_timestamp(self.ztp, r_earliest_pickup_time)
            latest_pickup_time = to_timestamp(self.ztp, r_latest_pickup_time)

            soft_pickup_constraint = TimepointConstraint(name="pickup",
                                                         earliest_time=earliest_pickup_time.to_datetime(),
                                                         latest_time=latest_pickup_time.to_datetime())
            task.update_timepoint_constraint(**soft_pickup_constraint.to_dict())

    def update_delivery_constraint(self, task):
        pickup_constraint = task.get_timepoint_constraint("pickup")
        work_time = task.get_inter_timepoint_constraint("work_time")

        r_earliest_time = relative_to_ztp(self.ztp, pickup_constraint.earliest_time)
        r_latest_time = relative_to_ztp(self.ztp, pickup_constraint.latest_time)
        stn_prev_constraint = STNTimepointConstraint(name="pickup", r_earliest_time=r_earliest_time, r_latest_time=r_latest_time)
        inter_timepoint_constraint = STNInterTimepointConstraint(**work_time.to_dict())
        stn_delivery_constraint = self.stn.get_next_timepoint_constraint("delivery", stn_prev_constraint, inter_timepoint_constraint)

        earliest_time = to_timestamp(self.ztp, stn_delivery_constraint.r_earliest_time)
        latest_time = to_timestamp(self.ztp, stn_delivery_constraint.r_latest_time)

        delivery_constraint = TimepointConstraint(name="delivery",
                                                  earliest_time=earliest_time.to_datetime(),
                                                  latest_time=latest_time.to_datetime())
        task.update_timepoint_constraint(**delivery_constraint.to_dict())

    def previous_task_is_frozen(self, insertion_point):
        task_id = self.stn.get_task_id(insertion_point-1)
        previous_task = Task.get_task(task_id)
        if previous_task.frozen:
            return True
        return False

    def get_r_time_previous_task(self, insertion_point, node_type, earliest=True):
        task_id = self.stn.get_task_id(insertion_point-1)
        previous_task = Task.get_task(task_id)
        return self.dispatchable_graph.get_time(previous_task.task_id, node_type, earliest)

    def get_constraints(self, task):
        stn_timepoint_constraints = list()
        stn_inter_timepoint_constraints = list()

        for constraint in task.constraints.temporal.timepoint_constraints:
            r_earliest_time = relative_to_ztp(self.ztp, constraint.earliest_time)
            r_latest_time = relative_to_ztp(self.ztp, constraint.latest_time)
            stn_timepoint_constraints.append(STNTimepointConstraint(name=constraint.name,
                                                                    r_earliest_time=r_earliest_time,
                                                                    r_latest_time=r_latest_time))

        for constraint in task.constraints.temporal.inter_timepoint_constraints:
            stn_inter_timepoint_constraints.append(STNInterTimepointConstraint(**constraint.to_dict()))

        return stn_timepoint_constraints, stn_inter_timepoint_constraints
