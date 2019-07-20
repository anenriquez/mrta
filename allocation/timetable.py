class Timetable(object):
    def __init__(self, robot_ids, stp):

        self.stns = dict()
        self.dispatchable_graphs = dict()
        self.schedules = dict()
        self.stp = stp

        for robot_id in robot_ids:
            self.stns[robot_id] = self.stp.get_stn()
            self.dispatchable_graphs[robot_id] = self.stp.get_stn()
            self.schedules[robot_id] = self.stp.get_stn()

    def update_stn(self, robot_id, task, position):
        stn = self.stns.get(robot_id)
        stn.add_task(task, position)
        self.stns.update({robot_id: stn})

        return stn

    def update_dispatchable_graph(self, robot_id, stn):
        result_stp = self.stp.compute_dispatchable_graph(stn)
        stp_metric, dispatchable_graph = result_stp
        self.dispatchable_graphs.update({robot_id: dispatchable_graph})

        return dispatchable_graph

