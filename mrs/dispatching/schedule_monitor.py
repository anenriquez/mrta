import logging
from datetime import timedelta

from ropod.utils.timestamp import TimeStamp


class ScheduleMonitor:
    def __init__(self, freeze_window):
        """ Monitors the schedulability of tasks

        Args:

            freeze_window (float): Defines the time (minutes) within which a task can be scheduled
                        e.g, with a freeze window of 2 minutes, a task can be scheduled if its earliest
                        start navigation time is within the next 2 minutes.

        """
        self.logger = logging.getLogger('mrs.schedule_monitor')
        self.freeze_window = timedelta(seconds=freeze_window)
        self.logger.debug("Schedule Monitor started")

    def is_schedulable(self, start_time):
        current_time = TimeStamp()
        if start_time.get_difference(current_time) < self.freeze_window:
            return True
        return False

