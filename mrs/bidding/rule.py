from mrs.bidding.bid import Bid
from mrs.exceptions.allocation import NoSTPSolution
from fmlib.models.tasks import TimepointConstraints
from datetime import timedelta


class BiddingRule(object):
    def __init__(self, robustness_criterion, temporal_criterion):
        self.robustness_criterion = robustness_criterion
        self.temporal_criterion = temporal_criterion

    def compute_bid(self, robot_id, round_id, task_lot, position, timetable):
        timetable.add_task_to_stn(task_lot, position)

        try:
            timetable.solve_stp()
            timetable.compute_temporal_metric(self.temporal_criterion)

            if task_lot.constraints.hard:
                bid = Bid(robot_id, round_id, task_lot.task.task_id, timetable,
                          position=position,
                          risk_metric=timetable.risk_metric,
                          temporal_metric=timetable.temporal_metric)

            else:
                r_start_time = timetable.dispatchable_graph.get_time(task_lot.task.task_id, "start")
                start_time = timetable.zero_timepoint + timedelta(minutes=r_start_time)
                timetable.risk_metric = 1
                start_timepoint_constraints = task_lot.constraints.timepoint_constraints[0]

                r_earliest_start_time, r_latest_start_time = TimepointConstraints.relative_to_ztp(start_timepoint_constraints,
                                                                                                timetable.zero_timepoint)

                timetable.temporal_metric = abs(r_start_time - r_earliest_start_time)

                bid = Bid(robot_id, round_id, task_lot.task.task_id, timetable,
                          position=position,
                          risk_metric=timetable.risk_metric,
                          temporal_metric=timetable.temporal_metric,
                          hard_constraints=False,
                          alternative_start_time=start_time)

            return bid

        except NoSTPSolution:
            raise NoSTPSolution()

