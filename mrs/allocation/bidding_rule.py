from stn.exceptions.stp import NoSTPSolution

from mrs.messages.bid import Bid, SoftBid, Metrics


class BiddingRule(object):
    def __init__(self, temporal_criterion):
        self.temporal_criterion = temporal_criterion

    def compute_bid(self, robot_id, round_id, task, insertion_point, timetable, pre_task_action):
        try:
            stn, dispatchable_graph = timetable.solve_stp(task, insertion_point)
            dispatchable_graph.compute_temporal_metric(self.temporal_criterion)

            if task.constraints.hard:
                bid = Bid(task.task_id,
                          robot_id,
                          round_id,
                          insertion_point,
                          Metrics(dispatchable_graph.temporal_metric, dispatchable_graph.risk_metric),
                          pre_task_action)
            else:
                pickup_constraint = task.get_timepoint_constraint("pickup")
                temporal_metric = abs(pickup_constraint.earliest_time - task.request.earliest_pickup_time).total_seconds()
                risk_metric = 1
                alternative_start_time = pickup_constraint.earliest_time

                bid = SoftBid(task.task_id,
                              robot_id,
                              round_id,
                              insertion_point,
                              Metrics(temporal_metric, risk_metric),
                              pre_task_action,
                              alternative_start_time)

            bid.stn = stn
            bid.dispatchable_graph = dispatchable_graph

            return bid

        except NoSTPSolution:
            raise NoSTPSolution()

