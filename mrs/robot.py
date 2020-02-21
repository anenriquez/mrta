import argparse
import logging.config

from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.db.models.task import Task
from mrs.exceptions.execution import InconsistentSchedule
from mrs.execution.delay_recovery import DelayRecovery
from mrs.execution.executor import Executor
from mrs.execution.schedule_monitor import ScheduleMonitor
from mrs.messages.d_graph_update import DGraphUpdate
from mrs.messages.recover import ReAllocate, Abort, ReSchedule
from mrs.simulation.simulator import Simulator
from mrs.timetable.timetable import Timetable
from pymodm.errors import DoesNotExist
from ropod.structs.status import ActionStatus, TaskStatus as TaskStatusConst

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
        self.d_graph_update_received = False

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

    def d_graph_update_cb(self, msg):
        payload = msg['payload']
        self.logger.critical("Received DGraph update")
        d_graph_update = DGraphUpdate.from_payload(payload)
        d_graph_update.update_timetable(self.timetable)
        self.logger.debug("STN update %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph update %s", self.timetable.dispatchable_graph)
        self.d_graph_update_received = True

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
        self.logger.debug("Trigger abortion of task %s", task.task_id)
        task.update_status(TaskStatusConst.ABORTED)
        self.timetable.remove_task(task.task_id)
        recover = Abort(self.recovery_method, task.task_id)
        self.send_recover_msg(recover)

    def re_schedule(self, task):
        self.logger.debug("Trigger rescheduling")
        recover = ReSchedule(self.recovery_method, task.task_id)
        self.send_recover_msg(recover)

    def schedule(self, task):
        try:
            self.schedule_monitor.schedule(task)
        except InconsistentSchedule:
            if "re-allocate" in self.recovery_method:
                self.re_allocate(task)
            else:
                self.abort(task)

    def start_execution(self, task):
        self.executor.start_execution(task)

    def execute(self):
        if self.executor.action_progress.status == ActionStatus.COMPLETED:
            self.executor.complete_execution()

        elif not self.recovery_method.startswith("re-schedule") or\
                self.recovery_method.startswith("re-schedule") and self.d_graph_update_received:

            self.d_graph_update_received = False
            self.executor.execute()

            if self.schedule_monitor.recover(self.executor.current_task, self.executor.action_progress.is_consistent):
                self.recover(self.executor.current_task)

            self.executor.update_action_progress()

    def recover(self, task):
        if self.recovery_method == "re-allocate":
            next_task = self.timetable.get_next_task(task)
            self.re_allocate(next_task)

        elif self.recovery_method.startswith("re-schedule"):
            self.re_schedule(self.executor.current_task)

        elif self.recovery_method == "abort":
            next_task = self.timetable.get_next_task(task)
            self.abort(next_task)

    def process_tasks(self, tasks):
        for task in tasks:
            task_status = task.get_task_status(task.task_id)

            if task_status.status == TaskStatusConst.DISPATCHED and self.timetable.has_task(task.task_id):
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
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('--experiment', type=str, action='store', help='Experiment_name')
    parser.add_argument('--approach', type=str, action='store', help='Approach name')
    args = parser.parse_args()

    config_params = get_config_params(args.file, experiment=args.experiment, approach=args.approach)

    print("Experiment: ", config_params.get("experiment"))
    print("Approach: ", config_params.get("approach"))

    config = Configurator(config_params, component_modules=_component_modules)
    components = config.config_robot(args.robot_id)
    robot = Robot(**components)

    robot.run()
