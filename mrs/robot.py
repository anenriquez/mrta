import argparse
import logging.config

from fmlib.utils.utils import load_file_from_module, load_yaml
from pymodm.errors import DoesNotExist
from ropod.structs.status import ActionStatus, TaskStatus as TaskStatusConst

from mrs.config.configurator import Configurator
from mrs.db.models.task import Task
from mrs.exceptions.execution import InconsistentSchedule
from mrs.execution.delay_recovery import DelayRecovery
from mrs.execution.executor import Executor
from mrs.execution.schedule_monitor import ScheduleMonitor
from mrs.messages.dispatch_queue_update import DispatchQueueUpdate
from mrs.messages.recover import ReAllocate, Abort, ReSchedule
from mrs.simulation.simulator import Simulator
from mrs.timetable.timetable import Timetable

_component_modules = {'simulator': Simulator,
                      'timetable': Timetable,
                      'executor': Executor,
                      'schedule_monitor': ScheduleMonitor,
                      'delay_recovery': DelayRecovery}


class Robot:
    def __init__(self, robot_id, api, executor, schedule_monitor, timetable, **kwargs):

        self.robot_id = robot_id
        self.api = api
        self.executor = executor
        self.schedule_monitor = schedule_monitor
        self.timetable = timetable
        self.timetable.fetch()

        self.tasks = list()
        self.queue_update_received = False

        self.api.register_callbacks(self)
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)
        self.logger.info("Initialized Robot %s", robot_id)

    @property
    def recovery_method(self):
        return self.schedule_monitor.recovery_method.name

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        if self.robot_id in task.assigned_robots:
            self.logger.debug("Received task %s", task.task_id)
            task.update_status(TaskStatusConst.DISPATCHED)
            task.freeze()

    def dispatch_queue_update_cb(self, msg):
        payload = msg['payload']
        self.logger.debug("Received dispatch queue update")
        d_queue_update = DispatchQueueUpdate.from_payload(payload)
        if self.recovery_method.startswith("re-schedule"):
            d_queue_update.update_timetable(self.timetable, replace=True)
        else:
            d_queue_update.update_timetable(self.timetable, replace=False)

        self.logger.debug("STN update %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph update %s", self.timetable.dispatchable_graph)
        self.queue_update_received = True

    def send_recover_msg(self, recover):
        msg = self.api.create_message(recover)
        self.api.publish(msg)

    def re_allocate(self, task):
        self.logger.debug("Trigger re-allocation of task %s", task.task_id)
        task.update_status(TaskStatusConst.UNALLOCATED)
        self.timetable.remove_task(task.task_id)
        recover = ReAllocate(self.recovery_method, task.task_id)
        self.send_recover_msg(recover)

    def abort(self, task):
        status = TaskStatusConst.ABORTED
        task.update_status(status)
        self.timetable.remove_task(task.task_id)
        recover = Abort(self.recovery_method, task.task_id, status)
        self.send_recover_msg(recover)

    def schedule(self, task):
        try:
            self.schedule_monitor.schedule(task)
        except InconsistentSchedule:
            self.re_allocate(task)

    def start_execution(self, task):
        self.executor.start_execution(task)

    def execute(self):
        if self.executor.action_progress.status == ActionStatus.COMPLETED:
            self.executor.complete_execution()

        elif not self.recovery_method.startswith("re-schedule") or\
                self.recovery_method.startswith("re-schedule") and self.queue_update_received:

            self.queue_update_received = False
            self.executor.execute()

            if self.schedule_monitor.recover(self.executor.current_task, self.executor.action_progress.is_consistent):
                self.logger.debug("Applying recovery method: %s", self.recovery_method)
                self.recover(self.executor.current_task)

    def recover(self, task):
        if self.recovery_method == "re-allocate":
            task.mark_as_delayed()
            next_task = self.timetable.get_next_task(task)
            self.re_allocate(next_task)

        elif self.recovery_method.startswith("re-schedule"):
            recover = ReSchedule(self.recovery_method, self.executor.current_task.task_id)
            self.send_recover_msg(recover)

        elif self.recovery_method == "abort":
            next_task = self.timetable.get_next_task(task)
            self.abort(next_task)

    def process_tasks(self, tasks):
        for task in tasks:
            task_status = task.get_task_status(task.task_id)

            if task_status.status == TaskStatusConst.DISPATCHED and self.queue_update_received:
                self.schedule(task)

            # For real-time execution add is_executable condition
            if task_status.status == TaskStatusConst.SCHEDULED:
                self.start_execution(task)

    def run(self):
        try:
            self.api.start()
            while True:
                try:
                    tasks = Task.get_tasks_by_robot(self.robot_id)
                    if self.executor.current_task is None:
                        self.process_tasks(tasks)
                    else:
                        self.execute()
                except DoesNotExist:
                    pass
                self.api.run()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.robot_id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('--case', type=int, action='store', default=1, help='Test case number')
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    args = parser.parse_args()
    case = args.case

    test_cases = load_file_from_module('mrs.tests.cases', 'test-cases.yaml')
    test_config = {case: load_yaml(test_cases).get(case)}
    test_case = test_config.popitem()[1]

    config = Configurator(args.file, component_modules=_component_modules, test_case=test_case)
    components = config.config_robot(args.robot_id)

    robot = Robot(**components)
    robot.run()
