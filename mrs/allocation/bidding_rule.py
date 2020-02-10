from mrs.messages.bid import Bid, Metrics
from stn.exceptions.stp import NoSTPSolution


class BiddingRule(object):
    def __init__(self, temporal_criterion, timetable):
        self.temporal_criterion = temporal_criterion
        self.timetable = timetable

    def compute_bid(self, stn, robot_id, round_id, task, allocation_info):
        try:
            dispatchable_graph = self.timetable.compute_dispatchable_graph(stn)
            dispatchable_graph.compute_temporal_metric(self.temporal_criterion)

            if task.constraints.hard:
                bid = Bid(task.task_id,
                          robot_id,
                          round_id,
                          Metrics(dispatchable_graph.temporal_metric, dispatchable_graph.risk_metric))
            else:
                pickup_constraint = task.get_timepoint_constraint("pickup")
                temporal_metric = abs(pickup_constraint.earliest_time - task.request.earliest_pickup_time).total_seconds()
                risk_metric = 1
                alternative_start_time = pickup_constraint.earliest_time

                bid = Bid(task.task_id,
                          robot_id,
                          round_id,
                          Metrics(temporal_metric, risk_metric),
                          alternative_start_time=alternative_start_time)

            bid.set_allocation_info(allocation_info)
            bid.set_stn(stn)
            bid.set_dispatchable_graph(dispatchable_graph)

            return bid

        except NoSTPSolution:
            raise NoSTPSolution()
