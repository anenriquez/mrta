import logging

import numpy as np
from mrs.exceptions.execution import InconsistentSchedule
from mrs.exceptions.execution import MissingDispatchableGraph
from mrs.messages.archive_task import ArchiveTask
from mrs.scheduling.monitor import ScheduleMonitor
from ropod.structs.task import TaskStatus as TaskStatusConst


class ExecutorInterface:
    def __init__(self, robot_id,
                 stp_solver,
                 allocation_method,
                 corrective_measure,
                 max_seed,
                 **kwargs):
        self.robot_id = robot_id
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')
        time_resolution = kwargs.get('time_resolution', 0.5)
        self.delay_n_standard_dev = kwargs.get('delay_n_standard_dev', 0)
        self.tasks = list()
        self.archived_tasks = list()
        self.task_to_archive = None
        self.schedule_monitor = ScheduleMonitor(robot_id,
                                                stp_solver,
                                                allocation_method,
                                                corrective_measure,
                                                time_resolution,
                                                self.tasks)
        self.logger = logging.getLogger("mrs.executor.interface.%s" % self.robot_id)
        self.logger.debug("Executor interface initialized %s", self.robot_id)
        random_seed = np.random.randint(max_seed)
        self.random_state = np.random.RandomState(random_seed)

    def execute(self, task):
        self.logger.info("Starting execution of task %s", task.task_id)
        travel_constraint = task.get_inter_timepoint_constraint("travel_time")
        travel_duration = travel_constraint.get_duration(self.random_state, self.delay_n_standard_dev)
        start_time = self.schedule_monitor.dispatchable_graph.get_time(task.task_id, 'start')
        pickup_time = start_time + travel_duration
        self.logger.info("Task %s, assigning pickup_time %s", task.task_id, pickup_time)
        self.schedule_monitor.assign_timepoint(pickup_time, task.task_id, 'pickup')

        work_constraint = task.get_inter_timepoint_constraint("work_time")
        work_duration = work_constraint.get_duration(self.random_state, self.delay_n_standard_dev)
        delivery_time = pickup_time + work_duration
        self.logger.info("Task %s, assigning delivery_time %s", task.task_id, delivery_time)
        self.schedule_monitor.assign_timepoint(delivery_time, task.task_id, 'delivery')

        self.archive_task(task)

    def archive_task(self, task):
        self.logger.critical("Deleting task: %s", task.task_id)
        task.update_status(TaskStatusConst.COMPLETED)
        self.tasks.remove(task)
        self.archived_tasks.append(task)
        node_id = self.schedule_monitor.remove_task(task.task_id)
        archive_task = ArchiveTask(self.robot_id, task.task_id, node_id)
        # Provisional hack
        self.task_to_archive = archive_task
        archive_task_msg = self.api.create_message(archive_task)
        self.api.publish(archive_task_msg)

    def run(self):
        for task in self.tasks:
            if task.status.status == TaskStatusConst.DISPATCHED:
                try:
                    scheduled_task = self.schedule_monitor.schedule(task)
                    scheduled_task.update_status(TaskStatusConst.SCHEDULED)
                except MissingDispatchableGraph:
                    pass
                except InconsistentSchedule:
                    pass

            if task.status.status == TaskStatusConst.SCHEDULED and task.is_executable():
                task.update_status(TaskStatusConst.ONGOING)
                self.execute(task)
