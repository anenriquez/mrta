from mrs.structs.bid import Bid
from mrs.exceptions.task_allocation import NoSTPSolution


class BiddingRule(object):
    def __init__(self, robustness_criterion, temporal_criterion):
        self.robustness_criterion = robustness_criterion
        self.temporal_criterion = temporal_criterion

    def compute_bid(self, robot_id, round_id, task, position, timetable):
        timetable.add_task_to_stn(task, position)
        try:
            timetable.solve_stp()
            timetable.compute_temporal_metric(self.temporal_criterion)

            if task.hard_constraints:
                bid = Bid(robot_id, round_id, task.id, timetable,
                          position=position,
                          risk_metric=timetable.risk_metric,
                          temporal_metric=timetable.temporal_metric)

            else:
                navigation_start_time = timetable.dispatchable_graph.get_task_navigation_start_time(task.id)
                timetable.risk_metric = 1
                timetable.temporal_metric = abs(navigation_start_time - task.earliest_start_time),

                bid = Bid(robot_id, round_id, task.id, timetable,
                          position=position,
                          risk_metric=timetable.risk_metric,
                          temporal_metric=timetable.temporal_metric,
                          hard_constraints=False,
                          alternative_start_time=navigation_start_time)

            return bid

        except NoSTPSolution:
            raise NoSTPSolution()

