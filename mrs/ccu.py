import argparse
import logging.config

from fmlib.models.tasks import TaskPlan
from planner.planner import Planner
from ropod.structs.status import TaskStatus as TaskStatusConst
from ropod.utils.uuid import generate_uuid

from mrs.allocation.auctioneer import Auctioneer
from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.db.models.actions import GoTo
from mrs.db.models.performance.robot import RobotPerformance
from mrs.db.models.performance.task import TaskPerformance
from mrs.db.models.task import Task, InterTimepointConstraint
from mrs.execution.delay_recovery import DelayRecovery
from mrs.execution.dispatcher import Dispatcher
from mrs.execution.fleet_monitor import FleetMonitor
from mrs.performance.tracker import PerformanceTracker
from mrs.simulation.simulator import Simulator, SimulatorInterface
from mrs.timetable.manager import TimetableManager
from mrs.timetable.monitor import TimetableMonitor

_component_modules = {'simulator': Simulator,
                      'timetable_manager': TimetableManager,
                      'auctioneer': Auctioneer,
                      'fleet_monitor': FleetMonitor,
                      'dispatcher': Dispatcher,
                      'planner': Planner,
                      'delay_recovery': DelayRecovery,
                      'timetable_monitor': TimetableMonitor,
                      'performance_tracker': PerformanceTracker,
                      }


class CCU:

    def __init__(self, components, **kwargs):

        self.auctioneer = components.get('auctioneer')
        self.fleet_monitor = components.get('fleet_monitor')
        self.dispatcher = components.get('dispatcher')
        self.planner = components.get('planner')
        self.timetable_manager = components.get('timetable_manager')
        self.timetable_monitor = components.get("timetable_monitor")
        self.simulator_interface = SimulatorInterface(components.get('simulator'))
        self.performance_tracker = components.get("performance_tracker")

        self.api = components.get('api')
        self.ccu_store = components.get('ccu_store')

        self.api.register_callbacks(self)
        self.logger = logging.getLogger("mrs.ccu")
        self.logger.info("Initialized CCU")

        self.task_plans = dict()

    def start_test_cb(self, msg):
        self.simulator_interface.stop()
        initial_time = msg["payload"]["initial_time"]
        self.logger.info("Start test at %s", initial_time)

        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        for robot_id in self.auctioneer.robot_ids:
            RobotPerformance.create_new(robot_id=robot_id)
        for task in tasks:
            self.task_plans[task.task_id] = self.get_task_plan(task)
            TaskPerformance.create_new(task_id=task.task_id)

        self.simulator_interface.start(initial_time)

        self.auctioneer.allocate(tasks)

    def get_task_plan(self, task):
        path = self.planner.get_path(task.request.pickup_location, task.request.delivery_location)

        mean, variance = self.get_plan_work_time(path)
        work_time = InterTimepointConstraint(name="work_time", mean=mean, variance=variance)
        task.update_inter_timepoint_constraint(work_time.name, work_time.mean, work_time.variance)

        task_plan = TaskPlan()
        action = GoTo(action_id=generate_uuid(),
                      type="PICKUP-TO-DELIVERY",
                      locations=path,
                      estimated_duration=work_time)
        task_plan.actions.append(action)

        return task_plan

    def get_plan_work_time(self, plan):
        mean, variance = self.planner.get_estimated_duration(plan)
        return mean, variance

    def process_allocation(self):
        while self.auctioneer.allocations:
            task_id, robot_ids = self.auctioneer.allocations.pop(0)
            task = self.auctioneer.allocated_tasks.get(task_id)
            task.assign_robots(robot_ids)
            task_plan = self.task_plans[task.task_id]
            task.update_plan(robot_ids, task_plan)
            self.logger.debug('Task plan of task %s updated', task.task_id)
            self.update_allocation_metrics()

            for robot_id in robot_ids:
                self.dispatcher.send_d_graph_update(robot_id)

            self.auctioneer.finish_round()

    def update_allocation_metrics(self):
        allocation_info = self.auctioneer.winning_bid.get_allocation_info()
        task = Task.get_task(allocation_info.new_task.task_id)
        self.performance_tracker.update_allocation_metrics(task)
        if allocation_info.next_task:
            task = Task.get_task(allocation_info.next_task.task_id)
            self.performance_tracker.update_allocation_metrics(task, only_constraints=True)

    def run(self):
        try:
            self.api.start()
            while True:
                self.auctioneer.run()
                self.dispatcher.run()
                self.timetable_monitor.run()
                self.process_allocation()
                self.performance_tracker.run()
                self.api.run()
        except (KeyboardInterrupt, SystemExit):
            self.api.shutdown()
            self.simulator_interface.stop()
            self.logger.info('CCU is shutting down')

    def shutdown(self):
        self.api.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('--experiment', type=str, action='store', help='Experiment_name')
    parser.add_argument('--approach', type=str, action='store', help='Approach name')
    args = parser.parse_args()

    config_params = get_config_params(args.file, experiment=args.experiment, approach=args.approach)

    print("Experiment: ", config_params.get("experiment"))
    print("Approach: ", config_params.get("approach"))

    config = Configurator(config_params, component_modules=_component_modules)
    components_ = config.config_ccu()
    ccu = CCU(components_)

    ccu.run()
