import argparse
import logging.config

from fmlib.models.tasks import TaskPlan
from fmlib.utils.utils import load_file_from_module, load_yaml
from planner.planner import Planner
from ropod.structs.status import TaskStatus as TaskStatusConst
from ropod.utils.uuid import generate_uuid

from mrs.allocation.auctioneer import Auctioneer
from mrs.config.configurator import Configurator
from mrs.db.models.actions import GoTo
from mrs.db.models.task import InterTimepointConstraint
from mrs.db.models.task import Task
from mrs.dispatching.dispatcher import Dispatcher
from mrs.execution.delay_recovery import DelayRecovery
from mrs.simulation.simulator import Simulator, SimulatorInterface
from mrs.timetable.timetable_manager import TimetableManager
from mrs.timetable.timetable_monitor import TimetableMonitor

_component_modules = {'simulator': Simulator,
                      'timetable_manager': TimetableManager,
                      'auctioneer': Auctioneer,
                      'dispatcher': Dispatcher,
                      'planner': Planner,
                      'delay_recovery': DelayRecovery,
                      'timetable_monitor': TimetableMonitor,
                      }


class CCU:

    def __init__(self, components, **kwargs):

        self.auctioneer = components.get('auctioneer')
        self.dispatcher = components.get('dispatcher')
        self.planner = components.get('planner')
        self.timetable_manager = components.get('timetable_manager')
        self.timetable_monitor = components.get("timetable_monitor")
        self.simulator_interface = SimulatorInterface(components.get('simulator'))

        self.api = components.get('api')
        self.ccu_store = components.get('ccu_store')

        self.api.register_callbacks(self)
        self.logger = logging.getLogger("mrs.ccu")
        self.logger.info("Initialized CCU")

        self.task_plans = dict()

    def start_test_cb(self, msg):
        self.logger.debug("Start test msg received")
        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        for task in tasks:
            self.task_plans[task.task_id] = self.get_task_plan(task)
        self.auctioneer.allocate(tasks)
        self.simulator_interface.start()

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
        while self.auctioneer.allocations and self.auctioneer.round.finished:
            task_id, robot_ids = self.auctioneer.allocations.pop(0)
            self.logger.debug("Processing allocation of task: %s", task_id)
            task = self.auctioneer.allocated_tasks.get(task_id)
            task.assign_robots(robot_ids)
            self.update_task_plan(robot_ids)

            for robot_id in robot_ids:
                # TODO: Send g_graph only if it is diff from previous version
                self.dispatcher.send_d_graph_update(robot_id)

    def update_task_plan(self, robot_ids):
        for pre_task_action in self.auctioneer.pre_task_actions:
            task = Task.get_task(pre_task_action.task_id)
            task_plan = self.task_plans[task.task_id]
            if [action for action in task_plan.actions if action.type == "ROBOT-TO-PICKUP"]:
                task_plan.actions[0] = pre_task_action
            else:
                task_plan.actions.insert(0, pre_task_action)

            task.update_plan(robot_ids, task_plan)
            self.logger.debug('Task plan of task %s updated', task.task_id)
        self.auctioneer.pre_task_actions = list()

    def run(self):
        try:
            self.api.start()
            while True:
                self.auctioneer.run()
                self.dispatcher.run()
                self.timetable_monitor.run()
                self.process_allocation()
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
    parser.add_argument('--case', type=int, action='store', default=1, help='Test case number')
    args = parser.parse_args()
    case = args.case

    test_cases = load_file_from_module('mrs.tests.cases', 'test-cases.yaml')
    test_config = {case: load_yaml(test_cases).get(case)}
    test_case = test_config.popitem()[1]

    config = Configurator(args.file, component_modules=_component_modules, test_case=test_case)
    components_ = config.config_ccu()
    ccu = CCU(components_)

    ccu.run()
