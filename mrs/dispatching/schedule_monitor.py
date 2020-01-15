import logging
from datetime import timedelta

from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution

from mrs.messages.assignment_update import AssignmentUpdate


class ScheduleMonitor:
    def __init__(self, timetable_manager, freeze_window):
        """ Monitors the schedulability of tasks

        Args:

            freeze_window (float): Defines the time (minutes) within which a task can be scheduled
                        e.g, with a freeze window of 2 minutes, a task can be scheduled if its earliest
                        start navigation time is within the next 2 minutes.

        """
        self.logger = logging.getLogger('mrs.schedule_monitor')
        self.timetable_manager = timetable_manager
        self.freeze_window = timedelta(seconds=freeze_window)
        self.logger.debug("Schedule Monitor started")

    def is_schedulable(self, start_time):
        current_time = TimeStamp()
        if start_time.get_difference(current_time) < self.freeze_window:
            return True
        return False

    def assignment_update_cb(self, msg):
        payload = msg['payload']
        assignment_update = AssignmentUpdate.from_payload(payload)
        self.logger.info("Assignment Update received")
        timetable = self.timetable_manager.get_timetable(assignment_update.robot_id)
        stn = timetable.stn
        # TODO: Solve stp of substn

        for a in assignment_update.assignments:
            stn = self.assign_timepoint(stn, a)

        self.logger.info("Updated STN: %s", stn)

        try:
            dispatchable_graph = timetable.compute_dispatchable_graph(stn)
            self.logger.info("Updated DispatchableGraph %s: ", dispatchable_graph)
            timetable.stn = stn
            timetable.dispatchable_graph = dispatchable_graph
            self.timetable_manager.timetables.update({assignment_update.robot_id: timetable})
            timetable.store()
            self.timetable_manager.send_update_to = assignment_update.robot_id
        except NoSTPSolution:
            self.logger.warning("Temporal network becomes inconsistent")
            # TODO: Abort or trigger re-allocation of next task

    @staticmethod
    def assign_timepoint(stn, assignment):
        stn.assign_timepoint(assignment.assigned_time, assignment.task_id, assignment.node_type)
        stn.execute_timepoint(assignment.task_id, assignment.node_type)
        stn.execute_incoming_edge(assignment.task_id, assignment.node_type)
        stn.remove_old_timepoints()
        return stn


