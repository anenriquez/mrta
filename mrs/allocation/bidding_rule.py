from stn.exceptions.stp import NoSTPSolution

from mrs.messages.bid import Bid


class BiddingRule(object):
    def __init__(self, temporal_criterion):
        self.temporal_criterion = temporal_criterion

    def compute_bid(self, robot_id, round_id, task, insertion_point, timetable, travel_time):
        try:
            stn, dispatchable_graph = timetable.solve_stp(task, insertion_point)
            dispatchable_graph.compute_temporal_metric(self.temporal_criterion)

            if task.constraints.hard:
                bid = Bid(robot_id,
                          round_id,
                          task.task_id,
                          insertion_point=insertion_point,
                          travel_time=travel_time,
                          risk_metric=dispatchable_graph.risk_metric,
                          temporal_metric=dispatchable_graph.temporal_metric)

            else:
                pickup_constraint = task.get_timepoint_constraint("pickup")
                temporal_metric = (pickup_constraint.earliest_time - task.request.earliest_pickup_time).total_seconds()
                timetable.temporal_metric = abs(temporal_metric)

                bid = Bid(robot_id,
                          round_id,
                          task.task_id,
                          insertion_point=insertion_point,
                          travel_time=travel_time,
                          risk_metric=1,
                          temporal_metric=timetable.temporal_metric,
                          alternative_start_time=pickup_constraint.earliest_time)

            bid.stn = stn
            bid.dispatchable_graph = dispatchable_graph

            return bid

        except NoSTPSolution:
            raise NoSTPSolution()

