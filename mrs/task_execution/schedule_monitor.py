import logging
from datetime import timedelta

from mrs.robot_base import RobotBase


class ScheduleMonitor(RobotBase):

    """ Maps allocation methods with their available corrective measures """

    corrective_measures = {'tessi': ['re-allocate'],
                           'tessi-srea': ['re-allocate'],
                           'tessi-drea': ['re-schedule'],
                           'tessi-dsc': ['re-allocate']
                           }

    def __init__(self, robot_id, stp_solver, freeze_window, allocation_method, corrective_measure, **kwargs):
        """ Includes methods to monitor the schedule of a robot's allocated tasks

       Args:

            robot_id (str):  id of the robot, e.g. ropod_001
            stp_solver (STP): Simple Temporal Problem object
            freeze_window (float): Defines the time (minutes) within which a task can be scheduled
                        e.g, with a freeze window of 2 minutes, a task can be scheduled if its earliest
                        start navigation time is within the next 2 minutes.
            allocation_method (str): Name of the allocation method
            corrective_measure (str): Name of the corrective measure

        """
        super().__init__(robot_id, stp_solver, **kwargs)
        self.logger = logging.getLogger('mrs.bidder.%s' % self.id)

        self.freeze_window = timedelta(minutes=freeze_window)

        available_corrective_measures = self.corrective_measures.get(allocation_method)

        if corrective_measure not in available_corrective_measures:
            self.logger.error("Corrective measure %s is not avaiable for method %s", corrective_measure, allocation_method)
            raise ValueError(corrective_measure)

        self.corrective_measure = corrective_measure


