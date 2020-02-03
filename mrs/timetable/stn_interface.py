from mrs.db.models.task import Task
from mrs.db.models.task import TimepointConstraint
from stn.task import InterTimepointConstraint as STNInterTimepointConstraint
from stn.task import Task as STNTask
from stn.task import TimepointConstraint as STNTimepointConstraint


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

    def to_stn_task(self, task, insertion_point):
        self.update_pickup_constraint(task, insertion_point)
        self.update_start_constraint(task, insertion_point)
        self.update_delivery_constraint(task)
        stn_timepoint_constraints, stn_inter_timepoint_constraints = self.get_constraints(task)
        stn_task = STNTask(task.task_id, stn_timepoint_constraints, stn_inter_timepoint_constraints)
        return stn_task

    def update_stn_task(self, task, insertion_point):
        self.update_start_constraint(task, insertion_point)
        stn_timepoint_constraints, stn_inter_timepoint_constraints = self.get_constraints(task)
        stn_task = STNTask(task.task_id, stn_timepoint_constraints, stn_inter_timepoint_constraints)
        return stn_task

    def update_start_constraint(self, task, insertion_point):
        pickup_constraint = task.get_timepoint_constraint("pickup")
        travel_time = task.get_inter_timepoint_constraint("travel_time")
        stn_start_constraint = self.stn.get_prev_timepoint_constraint("start",
                                                                      STNTimepointConstraint(**pickup_constraint.to_dict_relative_to_ztp(self.ztp)),
                                                                      STNInterTimepointConstraint(**travel_time.to_dict()))

        if insertion_point > 1 and self.previous_task_is_frozen(insertion_point):
            r_latest_delivery_time_previous_task = self.get_r_time_previous_task(insertion_point, "delivery", earliest=False)
            stn_start_constraint.r_earliest_time = max(stn_start_constraint.r_earliest_time,
                                                       r_latest_delivery_time_previous_task)

        earliest_time = TimepointConstraint.absolute_time(self.ztp, stn_start_constraint.r_earliest_time)
        latest_time = TimepointConstraint.absolute_time(self.ztp, stn_start_constraint.r_latest_time)
        start_constraint = TimepointConstraint(name="start",
                                               earliest_time=earliest_time,
                                               latest_time=latest_time)

        task.update_timepoint_constraint(**start_constraint.to_dict())

    def update_pickup_constraint(self, task, insertion_point):
        print("Updating pickup constraints")
        hard_pickup_constraint = task.get_timepoint_constraint("pickup")
        pickup_time_window = hard_pickup_constraint.latest_time - hard_pickup_constraint.earliest_time
        print("pickup_time_window: ", pickup_time_window)

        if not task.constraints.hard and insertion_point > 1:
            print("Constraints are soft and insertion point is", insertion_point)
            r_earliest_delivery_time_previous_task = self.get_r_time_previous_task(insertion_point, "delivery")
            print("r_earliest_delivery_time_previous_task: ", r_earliest_delivery_time_previous_task)
            travel_time = task.get_inter_timepoint_constraint("travel_time")
            earliest_pickup_time = r_earliest_delivery_time_previous_task + (travel_time.mean - 2*travel_time.variance**0.5)
            print("earliest_pickup_time: ", earliest_pickup_time)

            latest_pickup_time = earliest_pickup_time + pickup_time_window.total_seconds()
            print("latest_pickup_time:", latest_pickup_time)

            soft_pickup_constraint = TimepointConstraint(name="pickup",
                                                         earliest_time=TimepointConstraint.absolute_time(self.ztp, earliest_pickup_time),
                                                         latest_time=TimepointConstraint.absolute_time(self.ztp, latest_pickup_time))
            task.update_timepoint_constraint(**soft_pickup_constraint.to_dict())

            new_pickup_constraints = task.get_timepoint_constraint("pickup")
            print("New pickup constraints: ", new_pickup_constraints)

    def update_delivery_constraint(self, task):
        pickup_constraint = task.get_timepoint_constraint("pickup")
        work_time = task.get_inter_timepoint_constraint("work_time")
        stn_delivery_constraint = self.stn.get_next_timepoint_constraint("delivery",
                                                                         STNTimepointConstraint(**pickup_constraint.to_dict_relative_to_ztp(self.ztp)),
                                                                         STNInterTimepointConstraint(**work_time.to_dict()))
        earliest_time = TimepointConstraint.absolute_time(self.ztp, stn_delivery_constraint.r_earliest_time)
        latest_time = TimepointConstraint.absolute_time(self.ztp, stn_delivery_constraint.r_latest_time)
        delivery_constraint = TimepointConstraint(name="delivery",
                                                  earliest_time=earliest_time,
                                                  latest_time=latest_time)
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

        timepoint_constraints = task.get_timepoint_constraints()
        for constraint in timepoint_constraints:
            stn_timepoint_constraints.append(STNTimepointConstraint(**constraint.to_dict_relative_to_ztp(self.ztp)))

        inter_timepoint_constraints = task.get_inter_timepoint_constraints()
        for constraint in inter_timepoint_constraints:
            stn_inter_timepoint_constraints.append(STNInterTimepointConstraint(**constraint.to_dict()))

        return stn_timepoint_constraints, stn_inter_timepoint_constraints
