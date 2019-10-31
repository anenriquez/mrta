from mrs.bidding.bid import Bid
from stn.exceptions.stp import NoSTPSolution
from fmlib.models.tasks import TimepointConstraints
from datetime import timedelta


class BiddingRule(object):
    def __init__(self, temporal_criterion):
        self.temporal_criterion = temporal_criterion

    def compute_bid(self, robot_id, round_id, task_lot, insertion_point, timetable):
        try:
            stn, dispatchable_graph = timetable.solve_stp(task_lot, insertion_point)
            dispatchable_graph.compute_temporal_metric(self.temporal_criterion)

            if task_lot.constraints.hard:
                bid = Bid(robot_id,
                          round_id,
                          task_lot.task.task_id,
                          insertion_point=insertion_point,
                          risk_metric=dispatchable_graph.risk_metric,
                          temporal_metric=dispatchable_graph.temporal_metric)

            else:
                r_start_time = dispatchable_graph.get_time(task_lot.task.task_id, "start")
                start_time = timetable.zero_timepoint + timedelta(minutes=r_start_time)
                start_timepoint_constraints = task_lot.constraints.timepoint_constraints[0]

                r_earliest_start_time, r_latest_start_time = TimepointConstraints.relative_to_ztp(start_timepoint_constraints,
                                                                                                  timetable.zero_timepoint)

                timetable.temporal_metric = abs(r_start_time - r_earliest_start_time)

                bid = Bid(robot_id,
                          round_id,
                          task_lot.task.task_id,
                          insertion_point=insertion_point,
                          risk_metric=1,
                          temporal_metric=timetable.temporal_metric,
                          alternative_start_time=start_time)

            bid.stn = stn
            bid.dispatchable_graph = dispatchable_graph

            return bid

        except NoSTPSolution:
            raise NoSTPSolution()

