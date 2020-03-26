import logging
import time

from fmlib.models.actions import Action
from pymodm.context_managers import switch_collection
from ropod.structs.status import TaskStatus as TaskStatusConst, ActionStatus as ActionStatusConst
from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution

from fmlib.models.tasks import Task, InterTimepointConstraint
from mrs.messages.recover_task import RecoverTask
from mrs.messages.remove_task import RemoveTask
from mrs.messages.task_status import TaskStatus
from mrs.simulation.simulator import SimulatorInterface


class TimetableMonitor(SimulatorInterface):
    def __init__(self, auctioneer, dispatcher, delay_recovery, **kwargs):
        simulator = kwargs.get('simulator')
        super().__init__(simulator)

        self.auctioneer = auctioneer
        self.dispatcher = dispatcher
        self.timetable_manager = auctioneer.timetable_manager
        self.recovery_method = delay_recovery.method
        self.api = kwargs.get('api')

        self.tasks_to_remove = list()
        self.tasks_to_reallocate = list()
        self.completed_tasks = list()
        self.deleting_task = False
        self.processing_task = False
        self.logger = logging.getLogger("mrs.timetable.monitor")

    def task_status_cb(self, msg):
        while self.deleting_task:
            time.sleep(0.1)

        self.processing_task = True

        payload = msg['payload']
        timestamp = TimeStamp.from_str(msg["header"]["timestamp"])
        task_status = TaskStatus.from_payload(payload)
        task = Task.get_task(task_status.task_id)
        self.logger.debug("Received task status message for task %s by %s", task_status.task_id, task_status.robot_id)

        if not task.status.progress:
            task.update_progress(task_status.task_progress.action_id, task_status.task_progress.action_status.status)
        action_progress = task.status.progress.get_action(task_status.task_progress.action_id)

        if task_status.delayed:
            task.delayed = True

        if task_status.task_status == TaskStatusConst.ONGOING:
            self._update_timetable(task, task_status, action_progress, timestamp)
            self._update_task_schedule(task, task_status.task_progress, action_progress, timestamp)
            self._update_task_progress(task, task_status.task_progress, action_progress, timestamp)
            task.update_status(task_status.task_status)

        elif task_status.task_status == TaskStatusConst.COMPLETED:
            self.logger.debug("Adding task %s to tasks to remove", task.task_id)
            self.tasks_to_remove.append((task, task_status.task_status))

        elif task_status.status in [TaskStatusConst.CANCELED, TaskStatusConst.ABORTED]:
            self._remove_task(task, task_status.status)

        self.processing_task = False

    def recover_task_cb(self, msg):
        payload = msg['payload']
        recover = RecoverTask.from_payload(payload)
        task = Task.get_task(recover.task_id)
        if recover.method == "re-allocate":
            self._re_allocate(task)
        elif recover.method == "abort":
            self._abort(task)
        elif recover.method == "re-schedule":
            self._re_schedule(task)

    def _update_timetable(self, task, task_status, action_progress, timestamp):
        self.logger.debug("Updating timetable of robot %s", task_status.robot_id)
        timetable = self.timetable_manager.get_timetable(task_status.robot_id)

        # Get relative time (referenced to the ztp)
        assigned_time = timestamp.get_difference(timetable.ztp).total_seconds()

        action = Action.get_action(task_status.task_progress.action_id)
        start_node, finish_node = action.get_node_names()

        if task_status.task_progress.action_status.status == ActionStatusConst.ONGOING and\
                action_progress.start_time is None:
            timetable.update_timetable(assigned_time, task.task_id, start_node)

        elif task_status.task_progress.action_status.status == ActionStatusConst.COMPLETED and\
                action_progress.finish_time is None:
            timetable.update_timetable(assigned_time, task.task_id, finish_node)
            timetable.execute_edge(task.task_id, start_node, finish_node)

        self.auctioneer.changed_timetable.append(task_status.robot_id)

        self.logger.debug("Updated stn: \n %s ", timetable.stn)
        self.logger.debug("Updated dispatchable graph: \n %s", timetable.dispatchable_graph)

    def _update_task_schedule(self, task, task_progress, action_progress, timestamp):
        first_action = task.plan[0].actions[0]
        last_action = task.plan[0].actions[-1]

        if task_progress.action_id == first_action.action_id and action_progress.start_time is None:
            self.logger.debug("Task %s start time %s", task.task_id, timestamp)
            task_schedule = {"start_time": timestamp.to_datetime(),
                             "finish_time": task.finish_time}
            task.update_schedule(task_schedule)

        elif task_progress.action_id == last_action.action_id and action_progress.finish_time is None:
            self.logger.debug("Task %s finish time %s", task.task_id, timestamp)
            task_schedule = {"start_time": task.start_time,
                             "finish_time": timestamp.to_datetime()}
            task.update_schedule(task_schedule)

    def _update_task_progress(self, task, task_progress, action_progress, timestamp):
        self.logger.debug("Updating task progress of task %s", task.task_id)

        kwargs = {}
        if task_progress.action_status.status == ActionStatusConst.ONGOING and action_progress.start_time is None:
            kwargs.update(start_time=timestamp.to_datetime())
        elif task_progress.action_status.status == ActionStatusConst.COMPLETED and action_progress.finish_time is None:
            kwargs.update(start_time=action_progress.start_time, finish_time=timestamp.to_datetime())

        task.update_progress(task_progress.action_id, task_progress.action_status.status, **kwargs)

    def _re_allocate(self, task):
        self.logger.critical("Re-allocating task %s", task.task_id)
        self._remove_task(task, TaskStatusConst.UNALLOCATED)
        task.assign_robots(list())
        task.plan = list()
        task.delayed = False
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
            next_task = timetable.get_next_task(task)
            self._re_compute_dispatchable_graph(timetable, next_task)

    def _re_compute_dispatchable_graph(self, timetable, next_task=None):
        self.logger.debug("Recomputing dispatchable graph of robot %s", timetable.robot_id)
        try:
            timetable.dispatchable_graph = timetable.compute_dispatchable_graph(timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", timetable.robot_id, timetable.dispatchable_graph)
            self.auctioneer.changed_timetable.append(timetable.robot_id)
            self.dispatcher.send_d_graph_update(timetable.robot_id)
        except NoSTPSolution:
            self.logger.warning("Temporal network is inconsistent")
            if next_task:
                self.recover(next_task)
            else:
                self.dispatcher.send_d_graph_update(timetable.robot_id)

    def recover(self, task):
        if self.recovery_method.name.endswith("abort"):
            self._abort(task)
        elif self.recovery_method.name.endswith("re-allocate"):
            self._re_allocate(task)

    def _remove_task(self, task, status):
        self.logger.critical("Deleting task %s from timetable and changing its status to %s", task.task_id, status)
        for robot_id in task.assigned_robots:
            timetable = self.timetable_manager.get_timetable(robot_id)
            next_task = timetable.get_next_task(task)

            if status == TaskStatusConst.COMPLETED:
                if next_task:
                    finish_current_task = timetable.stn.get_time(task.task_id, 'delivery', False)
                    timetable.stn.assign_earliest_time(finish_current_task, next_task.task_id, 'start', force=True)
                self.update_robot_poses(task)
                timetable.remove_task(task.task_id)

            else:
                prev_task = timetable.get_previous_task(task)
                timetable.remove_task(task.task_id)
                if prev_task and next_task:
                    self.update_pre_task_constraint(prev_task, next_task, timetable)

            self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)

            self.send_remove_task(task.task_id, status, robot_id)
            task.update_status(status)
            self._re_compute_dispatchable_graph(timetable, next_task)

    def update_pre_task_constraint(self, prev_task, task, timetable):
        self.logger.critical("Update pre_task constraint of task %s", task.task_id)
        prev_location = prev_task.request.delivery_location
        path = self.dispatcher.planner.get_path(prev_location, task.request.pickup_location)
        mean, variance = self.dispatcher.planner.get_estimated_duration(path)
        travel_time = InterTimepointConstraint(name="travel_time", mean=mean, variance=variance)

        stn_task = timetable.get_stn_task(task.task_id)
        task.update_inter_timepoint_constraint(**travel_time.to_dict())
        stn_task.update_inter_timepoint_constraint(**travel_time.to_dict())
        timetable.add_stn_task(stn_task)
        timetable.update_task(stn_task)

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
