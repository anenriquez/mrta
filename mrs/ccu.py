import argparse
import logging.config
import time

from fmlib.models.actions import GoTo
from fmlib.models.tasks import TaskPlan
from fmlib.models.tasks import TransportationTask as Task
from ropod.structs.status import TaskStatus as TaskStatusConst

from mrs.allocation.auctioneer import Auctioneer
from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.db.models.performance.robot import RobotPerformance
from mrs.db.models.performance.task import TaskPerformance
from mrs.execution.delay_recovery import DelayRecovery
from mrs.execution.dispatcher import Dispatcher
from mrs.execution.fleet_monitor import FleetMonitor
from mrs.performance.tracker import PerformanceTracker
from mrs.simulation.simulator import Simulator, SimulatorInterface
from mrs.timetable.monitor import TimetableMonitor
from mrs.timetable.timetable import TimetableManager

_component_modules = {
    'simulator': Simulator,
    'timetable_manager': TimetableManager,
    'auctioneer': Auctioneer,
    'fleet_monitor': FleetMonitor,
    'dispatcher': Dispatcher,
    'delay_recovery': DelayRecovery,
    'timetable_monitor': TimetableMonitor,
    'performance_tracker': PerformanceTracker,
}


class CCU:
    """Central Control Unit

    Args:
        components(dict): Components added to the CCU
        kwargs: Optional configuration arguments

    Attributes:
        auctioneer (obj): Opens allocation rounds: announces unallocated tasks to the robot proxies in the local network.
                          Receives bids
                          Elects a winner per allocation round
        fleet_monitor (obj): Updates robots' positions based on robot-pose messages
        dispatcher (obj): Sends task-queues to the robot and robot proxy
        timetable_monitor (obj): Updates robots' timetables based on execution information and applies recovery methods
        simulator_interface(obj): Controls the simulation clock time
        performance_tracker(obj): Stores performance metrics in the ccu_store
        api(obj): Communication middleware API
        ccu_store(obj): Database to store ccu information
        logger(obj): Logger object

    """

    def __init__(self, components, **kwargs):

        self.auctioneer = components.get('auctioneer')
        self.fleet_monitor = components.get('fleet_monitor')
        self.dispatcher = components.get('dispatcher')
        self.timetable_monitor = components.get("timetable_monitor")
        self.simulator_interface = SimulatorInterface(components.get('simulator'))
        self.performance_tracker = components.get("performance_tracker")

        self.api = components.get('api')
        self.ccu_store = components.get('ccu_store')

        self.api.register_callbacks(self)
        self.logger = logging.getLogger("mrs.ccu")
        self.logger.info("Initialized CCU")

    def configure(self, **kwargs):
        for key, value in kwargs.items():
            self.logger.debug("Adding %s", key)
            self.__dict__[key] = value

    def start_test_cb(self, msg):
        """ Starts test upon reception of start-test message

            * Reads all ``UNALLOCATED`` tasks from the ``ccu_store``
            * Create a RobotPerformance model per robot
            * Add plan (from pickup to delivery) to all tasks
            * Starts the simulation
            * Requests the auctioneer to allocate the tasks

        Args:
            msg: start-test message in json format

        """
        self.simulator_interface.stop()
        initial_time = msg["payload"]["initial_time"]
        self.logger.info("Start test at %s", initial_time)

        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        for robot_id in self.auctioneer.robot_ids:
            RobotPerformance.create_new(robot_id=robot_id)
        for task in tasks:
            self.add_task_plan(task)
            TaskPerformance.create_new(task_id=task.task_id)

        self.simulator_interface.start(initial_time)

        self.auctioneer.allocate(tasks)

    def add_task_plan(self, task):
        """ Adds task plan (from pickup to delivery) to the given task

        Args:
            task (obj)

        """
        path = self.dispatcher.get_path(task.request.pickup_location,
                                        task.request.delivery_location)

        mean, variance = self.get_task_duration(path)
        task.update_duration(mean, variance)

        action = GoTo.create_new(type="PICKUP-TO-DELIVERY", locations=path)
        action.update_duration(mean, variance)
        task_plan = TaskPlan(actions=[action])
        task.update_plan(task_plan)
        self.logger.debug('Task plan of task %s updated', task.task_id)

    def get_task_duration(self, plan):
        """ Gets the estimated duration (mean, variance) for executing the plan

        Args:
            plan (list): List of nodes to traverse

        Returns:
            float: mean
            float: variance

        """
        mean, variance = self.dispatcher.get_path_estimated_duration(plan)
        return mean, variance

    def process_allocation(self):
        """ Process new allocations:
            * Adds robot to task
            * Gets tentative schedule
            * Updates performance allocation metrics
            * Sends d-graph-update message

        """
        while self.auctioneer.allocations:
            task_id, robot_ids = self.auctioneer.allocations.pop(0)
            task = self.auctioneer.allocated_tasks.get(task_id)
            task.assign_robots(robot_ids)
            task_schedule = self.auctioneer.get_task_schedule(task_id, robot_ids[0])
            task.update_schedule(task_schedule)
            self.update_allocation_metrics()

            for robot_id in robot_ids:
                self.dispatcher.send_d_graph_update(robot_id)

    def update_allocation_metrics(self):
        """ Updates last's allocation performance metrics
        """
        allocation_time = self.auctioneer.allocation_times.pop(0)
        allocation_info = self.auctioneer.winning_bid.get_allocation_info()
        task = Task.get_task(allocation_info.new_task.task_id)
        self.performance_tracker.update_allocation_metrics(task, allocation_time)
        if allocation_info.next_task:
            task = Task.get_task(allocation_info.next_task.task_id)
            self.performance_tracker.update_allocation_metrics(task, only_constraints=True)

    def run(self):
        """ Runs the CCU components
        """
        try:
            self.api.start()
            while True:
                self.auctioneer.run()
                self.dispatcher.run()
                self.timetable_monitor.run()
                self.process_allocation()
                self.performance_tracker.run()
                self.api.run()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.api.shutdown()
            self.simulator_interface.stop()
            self.logger.info('CCU is shutting down')

    def shutdown(self):
        self.api.shutdown()


if __name__ == '__main__':
    from planner.planner import Planner

    parser = argparse.ArgumentParser()
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
    components_ = config.config_ccu()

    kwargs = {
        "planner": Planner(**config_params.get("planner")),
        "performance_tracker": components_.get("performance_tracker")
    }

    for name, c in components_.items():
        if hasattr(c, 'configure'):
            c.configure(**kwargs)

    ccu = CCU(components_)

    ccu.run()
