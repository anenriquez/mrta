import argparse
import logging.config

from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.execution.delay_recovery import DelayRecovery
from mrs.execution.executor import Executor
from mrs.execution.schedule_execution_monitor import ScheduleExecutionMonitor
from mrs.execution.scheduler import Scheduler
from mrs.simulation.simulator import Simulator
from mrs.timetable.timetable import Timetable

_component_modules = {
    'simulator': Simulator,
    'timetable': Timetable,
    'executor': Executor,
    'scheduler': Scheduler,
    'schedule_execution_monitor': ScheduleExecutionMonitor,
    'delay_recovery': DelayRecovery
}


class Robot:
    """ Includes components that run in the physical robot

    Args:
        robot_id (str): ID that uniquely identifies the robot, e.g., robot_001
        api (ob): Communication middleware API
        executor (obj): Executes robot actions
        schedule_execution_monitor (obj): Monitors the execution of the schedule and triggers delay recovery mechanisms
                                          when needed
        kwargs: Optional configuration arguments
    """

    def __init__(self, robot_id, api, executor, schedule_execution_monitor,
                 **kwargs):

        self.robot_id = robot_id
        self.api = api
        self.executor = executor
        self.schedule_execution_monitor = schedule_execution_monitor

        self.api.register_callbacks(self)
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)
        self.logger.info("Initialized Robot %s", robot_id)

    def run(self):
        """ Runs the robot components
        """
        try:
            self.api.start()
            while True:
                self.schedule_execution_monitor.run()
                self.executor.run()
                self.api.run()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.robot_id)
            self.api.shutdown()
            self.executor.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':
    from planner.planner import Planner

    parser = argparse.ArgumentParser()
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    parser.add_argument('--file',
                        type=str,
                        action='store',
                        help='Path to the config file')
    parser.add_argument('--experiment',
                        type=str,
                        action='store',
                        help='Experiment_name')
    parser.add_argument('--approach',
                        type=str,
                        action='store',
                        help='Approach name')
    args = parser.parse_args()

    config_params = get_config_params(args.file,
                                      experiment=args.experiment,
                                      approach=args.approach)
    config = Configurator(config_params, component_modules=_component_modules)
    components = config.config_robot(args.robot_id)
    robot = Robot(**components)

    for name, c in components.items():
        if hasattr(c, 'configure'):
            c.configure(planner=Planner(**config_params.get("executor")))

    robot.run()
