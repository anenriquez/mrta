import logging
from datetime import timedelta

from mrs.simulation.simulator import SimulatorInterface


class ScheduleMonitor(SimulatorInterface):
    def __init__(self, timetable_manager, freeze_window, **kwargs):
        """ Monitors the schedulability of tasks

        Args:

            freeze_window (float): Defines the time (minutes) within which a task can be scheduled
                        e.g, with a freeze window of 2 minutes, a task can be scheduled if its earliest
                        start navigation time is within the next 2 minutes.

        """
        simulator = kwargs.get('simulator')
        super().__init__(simulator)

        self.logger = logging.getLogger('mrs.schedule_monitor')
        self.timetable_manager = timetable_manager
        self.freeze_window = timedelta(seconds=freeze_window)
        self.logger.debug("Schedule Monitor started")

    def is_schedulable(self, start_time):
        current_time = self.get_current_timestamp()
        if start_time.get_difference(current_time) < self.freeze_window:
            return True
        return False

