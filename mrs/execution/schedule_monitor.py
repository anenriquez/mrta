import logging

from mrs.exceptions.execution import InconsistentSchedule
from mrs.execution.scheduler import Scheduler


class ScheduleMonitor:

    def __init__(self, robot_id, timetable, time_resolution, delay_recovery, allocation_method, **kwargs):
        """ Includes methods to monitor the schedule of a robot's allocated tasks
        """
        self.robot_id = robot_id
        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)

        self.timetable = timetable

        self.recovery_method = delay_recovery.method

        self.scheduler = Scheduler(robot_id, timetable, time_resolution)

        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def recover(self, task, last_assignment):
        """ Returns True if a recovery (preventive or corrective) should be applied
        A preventive recovery prevents delay of next_task. Applied BEFORE current task becomes inconsistent
        A corrective recovery prevents delay of next task. Applied AFTER current task becomes inconsistent

        task (Task) : current task
        last_assignment (Assignment): last assignment
        """

        return self.recovery_method.recover(self.timetable, task, last_assignment)

    def schedule(self, task):
        try:
            assignment = self.scheduler.schedule(task)
            self.logger.info("Task %s scheduled to start at %s", task.task_id, task.start_time)
            self.logger.debug("STN %s", self.timetable.stn)
            return assignment

        except InconsistentSchedule as e:
            raise InconsistentSchedule(e.earliest_time, e.latest_time)
