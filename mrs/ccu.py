import argparse
import logging.config
import time

from fmlib.models.requests import TransportationRequest
from fmlib.models.tasks import TaskPlan
from mrs.config.configurator import Configurator
from mrs.db.models.actions import GoTo
from mrs.db.models.task import InterTimepointConstraint
from mrs.db.models.task import Task
from mrs.db.models.task import TemporalConstraints
from mrs.messages.task_progress import TaskProgress
from ropod.structs.status import TaskStatus as TaskStatusConst
from ropod.utils.uuid import generate_uuid


class CCU:
    def __init__(self, config_file=None):
        self.logger = logging.getLogger("mrs.ccu")
        self.logger.info("Configuring CCU...")

        components = self.get_components(config_file)

        self.auctioneer = components.get('auctioneer')
        self.dispatcher = components.get('dispatcher')
        self.planner = components.get('planner')
        self.api = components.get('api')
        self.ccu_store = components.get('ccu_store')

        self.api.register_callbacks(self)
        self.logger.info("Initialized CCU")

        self.task_plans = dict()

    @staticmethod
    def get_components(config_file):
        config = Configurator(config_file)
        return config.config_ccu()

    def start_test_cb(self, msg):
        self.logger.debug("Start test msg received")
        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        for task in tasks:
            self.task_plans[task.task_id] = self.get_task_plan(task)
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

    def update_task_plan(self):
        while self.auctioneer.allocations and self.auctioneer.round.finished:
            task_id, robot_ids = self.auctioneer.allocations.pop(0)
            task = Task.get_task(task_id)
            task.assign_robots(robot_ids)

            task_plan = self.task_plans[task_id]
            pre_task_action = self.auctioneer.pre_task_actions.get(task_id)
            task_plan.actions.insert(0, pre_task_action)

            task.update_plan(robot_ids, task_plan)
            self.logger.debug('Task plan updated...')

    def task_progress_cb(self, msg):
        payload = msg['payload']
        task_progress = TaskProgress.from_payload(payload)
        task = Task.get_task(task_progress.task_id)

        if task_progress.status == TaskStatusConst.COMPLETED:
            self.auctioneer.archive_task(task_progress.task_id, task_progress.robot_id)
            self.dispatcher.timetable_manager.send_update_to = task_progress.robot_id
        elif task_progress.status == TaskStatusConst.UNALLOCATED:
            self.trigger_reallocation(task, task_progress.robot_id)
        elif task_progress.re_allocate_next:
            timetable = self.auctioneer.timetable_manager.get_timetable(task_progress.robot_id)
            next_task = timetable.get_next_task(task)
            self.trigger_reallocation(next_task, task_progress.robot_id)

    def trigger_reallocation(self, task, robot_id):
        self.logger.critical("Triggering reallocation")
        self.auctioneer.archive_task(task.task_id, robot_id, status=TaskStatusConst.ABORTED)
        self.dispatcher.timetable_manager.send_update_to = robot_id
        task_dict = task.to_dict()
        request = TransportationRequest.from_payload(task_dict.get("request"))
        constraints = TemporalConstraints.from_payload(task_dict.get("constraints"))
        Task.create_new(task_id=task.task_id, request=request, constraints=constraints)
        task.update_status(TaskStatusConst.UNALLOCATED)
        self.auctioneer.allocate(task)

    def run(self):
        try:
            self.api.start()

            while True:
                self.auctioneer.run()
                self.dispatcher.run()
                self.update_task_plan()
                self.api.run()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.api.shutdown()
            self.logger.info('FMS is shutting down')

    def shutdown(self):
        self.api.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')

    args = parser.parse_args()
    ccu = CCU(args.file)
    ccu.run()


