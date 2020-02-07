import logging

from fmlib.models.actions import Action
from mrs.db.models.task import Task
from mrs.messages.recover import ReAllocate, Abort, ReSchedule
from mrs.messages.remove_task import RemoveTask
from mrs.messages.task_progress import TaskProgress
from mrs.simulation.simulator import SimulatorInterface
from ropod.structs.status import TaskStatus as TaskStatusConst
from stn.exceptions.stp import NoSTPSolution


class TimetableMonitor(SimulatorInterface):
    def __init__(self, auctioneer, dispatcher, timetable_manager, **kwargs):
        simulator = kwargs.get('simulator')
        super().__init__(simulator)

        self.auctioneer = auctioneer
        self.dispatcher = dispatcher
        self.timetable_manager = timetable_manager
        self.api = kwargs.get('api')

        self.tasks_to_remove = list()
        self.logger = logging.getLogger("mrs.timetable.monitor")

    def task_progress_cb(self, msg):
        payload = msg['payload']
        progress = TaskProgress.from_payload(payload)
        self.logger.debug("Task progress received: %s", progress)

        task = Task.get_task(progress.task_id)
        robot_id = progress.robot_id
        action_progress = progress.action_progress

        if progress.status == TaskStatusConst.COMPLETED:
            self.tasks_to_remove.append((task, progress.status))

        elif progress.status in [TaskStatusConst.CANCELED, TaskStatusConst.ABORTED]:
            self._remove_task(task, progress.status)
        else:
            self._update_timetable(task, robot_id, action_progress)
            self._update_task_schedule(task, action_progress)
            self._update_task_progress(task, action_progress)
            task.update_status(progress.status)

    def re_allocate_cb(self, msg):
        payload = msg['payload']
        recover = ReAllocate.from_payload(payload)
        task = Task.get_task(recover.task_id)
        self._re_allocate(task)

    def abort_cb(self, msg):
        payload = msg['payload']
        recover = Abort.from_payload(payload)
        task = Task.get_task(recover.task_id)
        self._remove_task(task, recover.status)

    def re_schedule_cb(self, msg):
        payload = msg['payload']
        recover = ReSchedule.from_payload(payload)
        task = Task.get_task(recover.task_id)
        self._re_schedule(recover.method, task)

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
        self.auctioneer.allocated_tasks.pop(task.task_id)
        self.auctioneer.allocate(task)

    def _re_schedule(self, recovery_method, task):
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
                self.logger.warning("Temporal network becomes inconsistent")
                next_task = timetable.get_next_task(task)
                if next_task and recovery_method.endswith("abort"):
                    self.logger.debug("Aborting task %s", next_task.task_id)
                    self._remove_task(next_task, TaskStatusConst.ABORTED)
                elif next_task and recovery_method.endswith("re-allocate"):
                    self._re_allocate(next_task)
                else:
                    self.dispatcher.send_d_graph_update(robot_id)

    def _remove_task(self, task, status):
        self.logger.critical("Deleting task %s from timetable and changing its status to %s", task.task_id, status)
        for robot_id in task.assigned_robots:
            timetable = self.timetable_manager.get_timetable(robot_id)
            timetable.remove_task(task.task_id)
            self.auctioneer.changed_timetable.append(robot_id)
            self.dispatcher.send_d_graph_update(robot_id)
            self.send_remove_task(task.task_id, status, robot_id)
            task.unfreeze()
            task.update_status(status)

            self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

    def send_remove_task(self, task_id, status, robot_id):
        remove_task = RemoveTask(task_id, status)
        msg = self.api.create_message(remove_task)
        self.api.publish(msg, peer=robot_id + '_proxy')

    def run(self):
        # TODO: Check how this works outside simulation
        ready_to_be_removed = list()
        for task, status in self.tasks_to_remove:
            if task.finish_time < self.get_current_time():
                ready_to_be_removed.append((task, status))

        for task, status in ready_to_be_removed:
            self.tasks_to_remove.remove((task, status))
            self._remove_task(task, status)
