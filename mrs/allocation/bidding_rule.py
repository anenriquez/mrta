import math
from datetime import timedelta

from mrs.messages.bid import Bid, Metrics
from stn.exceptions.stp import NoSTPSolution


class BiddingRuleFactory(dict):
    def __init__(self):
        super().__init__()

    def register_bidding_rule(self, rule_name, bidding_rule):
        self[rule_name] = bidding_rule

    def get_bidding_rule(self, rule_name, timetable):
        bidding_rule = self.get(rule_name)

        if not bidding_rule:
            raise ValueError(rule_name)
        return bidding_rule(timetable)


class BiddingRuleBase:
    def __init__(self, temporal_criterion, timetable):
        self.temporal_criterion = temporal_criterion
        self.timetable = timetable

    def compute_metrics(self, dispatchable_graph, **kwargs):
        temporal_metric = dispatchable_graph.compute_temporal_metric(self.temporal_criterion)
        return Metrics(temporal_metric)

    def compute_bid(self, stn, robot_id, round_id, task, allocation_info):
        try:
            dispatchable_graph = self.timetable.compute_dispatchable_graph(stn)
            metrics = self.compute_metrics(dispatchable_graph, allocation_info=allocation_info)

            print("stn: ", stn)
            print("dispatchable graph: ", dispatchable_graph)

            if task.constraints.hard:
                bid = Bid(task.task_id,
                          robot_id,
                          round_id,
                          metrics)
            else:
                pickup_constraint = task.get_timepoint_constraint("pickup")
                temporal_metric = abs(pickup_constraint.earliest_time - task.request.earliest_pickup_time).total_seconds()
                metrics.objective = temporal_metric
                alternative_start_time = pickup_constraint.earliest_time

                bid = Bid(task.task_id,
                          robot_id,
                          round_id,
                          metrics,
                          alternative_start_time=alternative_start_time)

            if allocation_info.insertion_point == 1:
                r_earliest_start_time = dispatchable_graph.get_time(task.task_id, "start")
                earliest_start_time = self.timetable.ztp + timedelta(seconds=r_earliest_start_time)
                bid.earliest_start_time = earliest_start_time

            bid.set_allocation_info(allocation_info)
            bid.set_stn(stn)
            bid.set_dispatchable_graph(dispatchable_graph)

            return bid

        except NoSTPSolution:
            raise NoSTPSolution()


class Duration(BiddingRuleBase):
    def __init__(self, temporal_criterion, timetable, alpha):
        super().__init__(temporal_criterion, timetable)
        self.alpha = alpha

    def compute_metrics(self, dispatchable_graph, **kwargs):
        allocation_info = kwargs.get("allocation_info")
        temporal_metric = dispatchable_graph.compute_temporal_metric(self.temporal_criterion)

        mean = 0
        variance = 0

        if allocation_info.next_task:
            # Subtracting the independent random variables new_travel_time - previous_travel_time
            mean, variance = allocation_info.next_task.get_inter_timepoint_constraint("travel_time") - \
                             allocation_info.prev_version_next_task.get_inter_timepoint_constraint("travel_time")

        # Adding the travel_time and work_time of the new task
        for constraint in allocation_info.new_task.inter_timepoint_constraints:
            mean += constraint.mean
            variance += constraint.variance

        increment_in_duration = math.ceil(mean + 2*(variance**0.5))

        # Dual objective (like TeSSIduo)
        objective = self.alpha * temporal_metric + (1 - self.alpha) * increment_in_duration

        return Metrics(objective, dispatchable_graph.risk_metric)


class CompletionTimeRisk(BiddingRuleBase):
    def __init__(self, timetable):
        super().__init__("completion_time", timetable)

    def compute_metrics(self, dispatchable_graph, **kwargs):
        temporal_metric = dispatchable_graph.compute_temporal_metric(self.temporal_criterion)
        return Metrics(temporal_metric, dispatchable_graph.risk_metric)


class CompletionTime(BiddingRuleBase):
    def __init__(self, timetable):
        super().__init__("completion_time", timetable)


class Makespan(BiddingRuleBase):
    def __init__(self, timetable):
        super().__init__("makespan", timetable)


class CompletionDuration(Duration):
    def __init__(self, timetable, **kwargs):
        alpha = kwargs.get("alpha", 0.5)
        super().__init__("completion_time", timetable, alpha)


class MakespanDuration(Duration):
    def __init__(self, timetable, **kwargs):
        alpha = kwargs.get("alpha", 0.5)
        super().__init__("makespan", timetable, alpha)


bidding_rule_factory = BiddingRuleFactory()
bidding_rule_factory.register_bidding_rule('makespan', Makespan)
bidding_rule_factory.register_bidding_rule('completion_time', CompletionTime)
bidding_rule_factory.register_bidding_rule('completion_time_risk', CompletionTimeRisk)
bidding_rule_factory.register_bidding_rule('completion_time_duration', CompletionDuration)
bidding_rule_factory.register_bidding_rule('makespan_duration', MakespanDuration)
