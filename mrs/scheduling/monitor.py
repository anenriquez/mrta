import logging

from mrs.scheduling.scheduler import Scheduler


class ScheduleMonitor:

    """ Maps allocation methods with their available corrective measures """

    corrective_measures = {'tessi': ['re-allocate'],
                           'tessi-srea': ['re-allocate'],
                           'tessi-drea': ['re-schedule'],
                           'tessi-dsc': ['re-allocate']
                           }

    def __init__(self, robot_id,
                 stp_solver,
                 allocation_method,
                 corrective_measure):
        """ Includes methods to monitor the schedule of a robot's allocated tasks

       Args:

            robot_id (str):  id of the robot, e.g. ropod_001
            stp_solver (STP): Simple Temporal Problem object
            allocation_method (str): Name of the allocation method
            corrective_measure (str): Name of the corrective measure
        """
        self.robot_id = robot_id
        self.stp_solver = stp_solver
        self.corrective_measure = self.get_corrective_measure(allocation_method, corrective_measure)
        self.scheduler = Scheduler(self.stp_solver, self.robot_id)
        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)
        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def get_corrective_measure(self, allocation_method, corrective_measure):
        available_corrective_measures = self.corrective_measures.get(allocation_method)
        if corrective_measure not in available_corrective_measures:
            self.logger.error("Corrective measure %s is not available for method %s", corrective_measure, allocation_method)
            raise ValueError(corrective_measure)

        return corrective_measure

