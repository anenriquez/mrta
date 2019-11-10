import logging
from datetime import timedelta
from mrs.scheduling.scheduler import Scheduler
from mrs.execution.interface import ExecutorInterface


class ScheduleMonitor:

    """ Maps allocation methods with their available corrective measures """

    corrective_measures = {'tessi': ['re-allocate'],
                           'tessi-srea': ['re-allocate'],
                           'tessi-drea': ['re-schedule'],
                           'tessi-dsc': ['re-allocate']
                           }

    def __init__(self, robot_id, stp_solver, timetable, freeze_window, allocation_method, corrective_measure, **kwargs):
        """ Includes methods to monitor the schedule of a robot's allocated tasks

       Args:

            robot_id (str):  id of the robot, e.g. ropod_001
            stp_solver (STP): Simple Temporal Problem object
            freeze_window (float): Defines the time (minutes) within which a task can be scheduled
                        e.g, with a freeze window of 2 minutes, a task can be scheduled if its earliest
                        start navigation time is within the next 2 minutes.
            allocation_method (str): Name of the allocation method
            corrective_measure (str): Name of the corrective measure
            kwargs:
                api (API): object that provides middleware functionality
                robot_store (robot_store): interface to interact with the db

        """
        self.robot_id = robot_id
        self.stp_solver = stp_solver
        self.timetable = timetable
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)

        self.freeze_window = timedelta(minutes=freeze_window)
        self.corrective_measure = self.get_corrective_measure(allocation_method, corrective_measure)

        self.scheduler = Scheduler(self.stp_solver, self.robot_id)
        self.executor_interface = ExecutorInterface(self.robot_id)

        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def get_corrective_measure(self, allocation_method, corrective_measure):

        available_corrective_measures = self.corrective_measures.get(allocation_method)

        if corrective_measure not in available_corrective_measures:
            self.logger.error("Corrective measure %s is not available for method %s", corrective_measure, allocation_method)
            raise ValueError(corrective_measure)

        return corrective_measure

    def configure(self, **kwargs):
        api = kwargs.get('api')
        ccu_store = kwargs.get('ccu_store')
        if api:
            self.api = api
        if ccu_store:
            self.ccu_store = ccu_store



