import logging
import time

from fmlib.models.actions import Action
from pymodm.context_managers import switch_collection
from ropod.structs.status import TaskStatus as TaskStatusConst
from stn.exceptions.stp import NoSTPSolution

from mrs.db.models.task import Task
from mrs.messages.recover import ReAllocate, Abort, ReSchedule
from mrs.messages.remove_task import RemoveTask
from mrs.messages.task_progress import TaskProgress
from mrs.simulation.simulator import SimulatorInterface


class TimetableMonitor(SimulatorInterface):
    def __init__(self, auctioneer, dispatcher, timetable_manager, delay_recovery, **kwargs):
        simulator = kwargs.get('simulator')
        super().__init__(simulator)

        self.auctioneer = auctioneer
        self.dispatcher = dispatcher
        self.timetable_manager = timetable_manager
        self.recovery_method = delay_recovery.method
        self.api = kwargs.get('api')

        self.tasks_to_remove = list()
        self.tasks_to_reallocate = list()
        self.completed_tasks = list()
        self.deleting_task = False
        self.processing_task = False
        self.logger = logging.getLogger("mrs.timetable.monitor")

    def task_progress_cb(self, msg):
        while self.deleting_task:
            time.sleep(0.1)

        self.processing_task = True

        payload = msg['payload']
        progress = TaskProgress.from_payload(payload)
        self.logger.debug("Task progress received: %s", progress)

        task = Task.get_task(progress.task_id)

        robot_id = progress.robot_id
        action_progress = progress.action_progress

        if progress.delayed:
            task.mark_as_delayed()

        if progress.status == TaskStatusConst.ONGOING:
            self._update_timetable(task, robot_id, action_progress)
            self._update_task_schedule(task, action_progress)
            self._update_task_progress(task, action_progress)
            task.update_status(progress.status)

        elif progress.status == TaskStatusConst.COMPLETED:
            self.tasks_to_remove.append((task, progress.status))

        elif progress.status in [TaskStatusConst.CANCELED, TaskStatusConst.ABORTED]:
            self._remove_task(task, progress.status)

        self.processing_task = False

    def re_allocate_cb(self, msg):
        payload = msg['payload']
        recover = ReAllocate.from_payload(payload)
        task = Task.get_task(recover.task_id)
        self._re_allocate(task)

    def abort_cb(self, msg):
        payload = msg['payload']
        recover = Abort.from_payload(payload)
        task = Task.get_task(recover.task_id)
        self._abort(task)

    def re_schedule_cb(self, msg):
        payload = msg['payload']
        recover = ReSchedule.from_payload(payload)
        task = Task.get_task(recover.task_id)
        self._re_schedule(task)

    def _update_timetable(self, task, robot_id, action_progress):
        if action_progress.start_time and action_progress.finish_time:
            timetable = self.timetable_manager.get_timetable(robot_id)
            self.logger.debug("Updating timetable of robot %s", robot_id)
            action = Action.get_action(action_progress.action.action_id)
            start_node, finish_node = action.get_node_names()
            timetable.update_timetable(task.task_id, start_node, finish_node,
                                       action_progress.r_start_time, action_progress.r_finish_time)
            self.auctioneer.changed_timetable.append(robot_id)

            self.logger.debug("Updated stn: \n %s ", timetable.stn)
            self.logger.debug("Updated dispatchable graph: \n %s", timetable.dispatchable_graph)

    def _update_task_schedule(self, task, action_progress):
        first_action = task.plan[0].actions[0]
        last_action = task.plan[0].actions[-1]

        if action_progress.action.action_id == first_action.action_id and\
                action_progress.start_time and not task.start_time:
            self.logger.debug("Task %s start time %s", task.task_id, action_progress.start_time)
            task.update_start_time(action_progress.start_time)

        elif action_progress.action.action_id == last_action.action_id and\
                action_progress.finish_time and not task.finish_time:
            self.logger.debug("Task %s finish time %s", task.task_id, action_progress.finish_time)
            task.update_finish_time(action_progress.finish_time)

    def _update_task_progress(self, task, action_progress):
        self.logger.debug("Updating task progress of task %s", task.task_id)
        kwargs = {}
        if action_progress.start_time:
            kwargs.update(start_time=action_progress.start_time)
        if action_progress.finish_time:
            kwargs.update(finish_time=action_progress.finish_time)
        task.update_progress(action_progress.action.action_id, action_progress.status, **kwargs)

    def _re_allocate(self, task):
        self.logger.critical("Re-allocating task %s", task.task_id)
        self._remove_task(task, TaskStatusConst.UNALLOCATED)
        task.assign_robots(list())
        task.plan = list()
        task.unmark_as_delayed()
        task.save()
        self.auctioneer.allocated_tasks.pop(task.task_id)
        self.auctioneer.allocate(task)
        self.tasks_to_reallocate.append(task)

    def _abort(self, task):
        self.logger.critical("Aborting task %s", task.task_id)
        self._remove_task(task, TaskStatusConst.ABORTED)
        with switch_collection(Task, Task.Meta.archive_collection):
            task.assign_robots(list())

    def _re_schedule(self, task):
        for robot_id in task.assigned_robots:
            timetable = self.timetable_manager.get_timetable(robot_id)
            stn = timetable.stn
            self.logger.debug("Recomputing dispatchable graph of robot %s", robot_id)
            try:
                dispatchable_graph = timetable.compute_dispatchable_graph(stn)
                self.logger.debug("Updated DispatchableGraph %s: ", dispatchable_graph)
                timetable.dispatchable_graph = dispatchable_graph
                self.auctioneer.changed_timetable.append(robot_id)
                timetable.store()
                self.dispatcher.send_d_graph_update(robot_id)
            except NoSTPSolution:
                self.logger.warning("Temporal network is inconsistent")
                next_task = timetable.get_next_task(task)
                if next_task:
                    self.recover(next_task)
                else:
                    self.dispatcher.send_d_graph_update(robot_id)

    def recover(self, task):
        if self.recovery_method.name.endswith("abort"):
            self._abort(task)
        elif self.recovery_method.name.endswith("re-allocate"):
            self._re_allocate(task)

    def _remove_task(self, task, status):
        self.logger.critical("Deleting task %s from timetable and changing its status to %s", task.task_id, status)
        for robot_id in task.assigned_robots:
            timetable = self.timetable_manager.get_timetable(robot_id)

            if status == TaskStatusConst.COMPLETED:
                self.validate_next_tasks(timetable, task)
                self.update_robot_poses(task)

            timetable.remove_task(task.task_id)
            self.auctioneer.changed_timetable.append(robot_id)
            self.dispatcher.send_d_graph_update(robot_id)
            self.send_remove_task(task.task_id, status, robot_id)
            task.unfreeze()
            task.update_status(status)

            self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

    def validate_next_tasks(self, timetable, task_to_delete):
        # Get next task until the next task is valid
        tasks_to_recover = list()
        next_task = timetable.get_next_task(task_to_delete)
        if next_task:
            tasks_to_recover = self.check_next_task_validity(timetable, task_to_delete, next_task, tasks_to_recover)
            for task_to_recover in tasks_to_recover:
                self.recover(task_to_recover)

    def check_next_task_validity(self, timetable, task, next_task, tasks_to_recover):
        if timetable.is_next_task_invalid(task, next_task):
            tasks_to_recover.append(next_task)
            next_task = timetable.get_next_task(next_task)
            if next_task:
                self.check_next_task_validity(timetable, task, next_task, tasks_to_recover)
        return tasks_to_recover

    def send_remove_task(self, task_id, status, robot_id):
        remove_task = RemoveTask(task_id, status)
        msg = self.api.create_message(remove_task)
        self.api.publish(msg, peer=robot_id + '_proxy')

    def update_robot_poses(self, task):
        for robot_id in task.assigned_robots:
            x, y, theta = self.dispatcher.planner.get_pose(task.request.delivery_location)
            self.dispatcher.fleet_monitor.update_robot_pose(robot_id, x=x, y=y, theta=theta)

    def run(self):
        # TODO: Check how this works outside simulation
        ready_to_be_removed = list()
        if not self.processing_task:

            for task, status in self.tasks_to_remove:
                if task.finish_time < self.get_current_time():
                    self.deleting_task = True
                    ready_to_be_removed.append((task, status))

            for task, status in ready_to_be_removed:
                self.tasks_to_remove.remove((task, status))
                if status == TaskStatusConst.COMPLETED:
                    self.completed_tasks.append(task)
                self._remove_task(task, status)

        if self.deleting_task and not self.completed_tasks:
            self.deleting_task = False
