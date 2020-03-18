import argparse
import logging.config

from pymodm.errors import DoesNotExist
from ropod.structs.status import TaskStatus as TaskStatusConst

from mrs.config.configurator import Configurator
from mrs.config.params import get_config_params
from mrs.db.models.task import Task
from mrs.exceptions.execution import InconsistentSchedule
from mrs.execution.delay_recovery import DelayRecovery
from mrs.execution.executor import Executor
from mrs.execution.schedule_monitor import ScheduleMonitor
from mrs.execution.scheduler import Scheduler
from mrs.simulation.simulator import Simulator
from mrs.timetable.timetable import Timetable

_component_modules = {'simulator': Simulator,
                      'timetable': Timetable,
                      'executor': Executor,
                      'scheduler': Scheduler,
                      'schedule_monitor': ScheduleMonitor,
                      'delay_recovery': DelayRecovery}


class Robot:
    def __init__(self, robot_id, api, executor, scheduler, schedule_monitor, **kwargs):

        self.robot_id = robot_id
        self.api = api
        self.executor = executor
        self.scheduler = scheduler
        self.schedule_monitor = schedule_monitor
        self.timetable = schedule_monitor.timetable
        self.timetable.fetch()

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

    def schedule(self, task):
        try:
            self.scheduler.schedule(task)
        except InconsistentSchedule:
            if "re-allocate" in self.recovery_method:
                self.schedule_monitor.re_allocate(task)
            else:
                self.schedule_monitor.abort(task)

    def process_tasks(self, tasks):
        for task in tasks:
            task_status = task.get_task_status(task.task_id)

            if task_status.status == TaskStatusConst.DISPATCHED and self.timetable.has_task(task.task_id):
                self.schedule(task)

            # For real-time execution add is_executable condition
            if task_status.status == TaskStatusConst.SCHEDULED:
                self.schedule_monitor.update_current_task(task)

    def run(self):
        try:
            self.api.start()
            while True:
                try:
                    tasks = Task.get_tasks_by_robot(self.robot_id)
                    if self.schedule_monitor.current_task is None:
                        self.process_tasks(tasks)
                    else:
                        self.schedule_monitor.run()
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
