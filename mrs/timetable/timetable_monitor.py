import logging

from fmlib.models.actions import Action
from mrs.db.models.task import Task
from mrs.messages.assignment_update import AssignmentUpdate
from mrs.messages.re_allocate import ReAllocate
from mrs.messages.remove_task import RemoveTask
from mrs.messages.task_progress import TaskProgress
from mrs.simulation.simulator import SimulatorInterface
from ropod.structs.status import TaskStatus as TaskStatusConst
from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution


class TimetableMonitor(SimulatorInterface):
    def __init__(self, auctioneer, dispatcher, timetable_manager, delay_recovery, **kwargs):
        simulator = kwargs.get('simulator')
        super().__init__(simulator)

        self.auctioneer = auctioneer
        self.dispatcher = dispatcher
        self.timetable_manager = timetable_manager
        self.recovery_method = delay_recovery.method

        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        self.tasks_to_remove = list()

        self.logger = logging.getLogger("mrs.task.monitor")

    def task_progress_cb(self, msg):
        payload = msg['payload']
        progress = TaskProgress.from_payload(payload)
        self.logger.critical("Task progress received: %s", progress)

        task = Task.get_task(progress.task_id)
        robot_id = progress.robot_id
        action_progress = progress.action_progress

        if progress.status == TaskStatusConst.COMPLETED:
            self.tasks_to_remove.append((task, progress.status))

        elif progress.status in [TaskStatusConst.CANCELED, TaskStatusConst.ABORTED]:
            self.remove_task(task, progress.status)
        else:
            self._update_timetable(task, robot_id, action_progress)
            self._update_task_schedule(task, action_progress)
            self._update_task_progress(task, action_progress)
            task.update_status(progress.status)

    def _update_task_progress(self, task, action_progress):
        self.logger.debug("Updating task progress of task %s", task.task_id)
        task.update_progress(action_progress.action_id, action_progress.status)

    def _update_timetable(self, task, robot_id, action_progress):
        if action_progress.start_time and action_progress.finish_time:
            timetable = self.timetable_manager.get_timetable(robot_id)
            self.logger.debug("Updating timetable of robot %s", robot_id)
            action = Action.get_action(action_progress.action_id)
            start_node, finish_node = action.get_node_names()
            timetable.update_timetable(task.task_id, start_node, finish_node,
                                       action_progress.r_start_time, action_progress.r_finish_time)

            # print("Updated stn: ", timetable.stn)
            # timetable.stn.remove_old_timepoints()
            print("Updated stn: ", timetable.stn)
            print("Updated dispatchable graph: ", timetable.dispatchable_graph)

                # If it is not the last action, remove nodes from stn
                # last_action = task.plan[0].actions[-1]
                # if action_progress.action_id != last_action.action_id:
                #     print("Removing old timepoints")
                #     timetable.stn.remove_old_timepoints()
                #
                #     print("Updated stn: ", timetable.stn)

    def _update_task_schedule(self, task, action_progress):
        first_action = task.plan[0].actions[0]
        last_action = task.plan[0].actions[-1]

        if action_progress.action_id == first_action.action_id and\
                action_progress.start_time and not task.start_time:
            self.logger.debug("Task %s start time %s", task.task_id, action_progress.start_time)
            task.update_start_time(action_progress.start_time)

        elif action_progress.action_id == last_action.action_id and\
                action_progress.finish_time and not task.finish_time:
            self.logger.debug("Task %s finish time %s", task.task_id, action_progress.finish_time)
            task.update_finish_time(action_progress.finish_time)

    def assignment_update_cb(self, msg):
        payload = msg['payload']
        assignment_update = AssignmentUpdate.from_payload(payload)
        self.logger.debug("Assignment Update received")
        timetable = self.timetable_manager.get_timetable(assignment_update.robot_id)
        stn = timetable.stn

        for a in assignment_update.assignments:
            stn.assign_timepoint(a.assigned_time, a.task_id, a.node_type, force=True)
            stn.execute_timepoint(a.task_id, a.node_type)
            stn.execute_incoming_edge(a.task_id, a.node_type)
            stn.remove_old_timepoints()

        last_assignment = assignment_update.assignments.pop()
        last_executed_task = Task.get_task(last_assignment.task_id)

        self.logger.debug("Updated STN: %s", stn)
        timetable.stn = stn
        timetable.store()

        try:
            dispatchable_graph = timetable.compute_dispatchable_graph(stn)
            self.logger.debug("Updated DispatchableGraph %s: ", dispatchable_graph)
            timetable.dispatchable_graph = dispatchable_graph
            timetable.store()
            # TODO: Send different msg
            self.dispatcher.send_d_graph_update(assignment_update.robot_id)
        except NoSTPSolution:
            self.logger.warning("Temporal network becomes inconsistent")
            next_task = timetable.get_next_task(last_executed_task)
            if next_task:
                self.recover(next_task)
            else:
                self.dispatcher.send_d_graph_update(assignment_update.robot_id)

    def recover(self, task):
        if self.recovery_method.name.endswith("abort"):
            self.logger.debug("Aborting task %s", task.task_id)
            self.remove_task(task, TaskStatusConst.ABORTED)

        elif self.recovery_method.name.endswith("re-allocate"):
            self.re_allocate(task)

    def remove_task(self, task, status):
        self.logger.critical("Deleting task %s from timetable and changing its status to %s", task.task_id, status)
        for robot_id in task.assigned_robots:
            timetable = self.timetable_manager.get_timetable(robot_id)
            timetable.remove_task(task.task_id)
            self.auctioneer.deleted_a_task.append(robot_id)
            self.dispatcher.send_d_graph_update(robot_id)
            self.send_remove_task(task.task_id, status, robot_id)
            task.update_status(status)

            self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

    def send_remove_task(self, task_id, status, robot_id):
        remove_task = RemoveTask(task_id, status)
        msg = self.api.create_message(remove_task)
        self.api.publish(msg, peer=robot_id + '_proxy')

    def re_allocate(self, task):
        self.logger.critical("Re-allocating task %s", task.task_id)
        self.remove_task(task, TaskStatusConst.UNALLOCATED)
        self.auctioneer.allocated_tasks.pop(task.task_id)
        self.auctioneer.allocate(task)

    def re_allocate_cb(self, msg):
        payload = msg['payload']
        task_id = ReAllocate.from_payload(payload).task_id
        task = Task.get_task(task_id)
        self.re_allocate(task)

    def remove_task_cb(self, msg):
        payload = msg['payload']
        remove_task = RemoveTask.from_payload(payload)
        task = Task.get_task(remove_task.task_id)
        self.remove_task(task, remove_task.status)

    def run(self):
        # TODO: Check how this works outside simulation
        ready_to_be_removed = list()
        for task, status in self.tasks_to_remove:
            if task.finish_time < self.get_current_time():
                ready_to_be_removed.append((task, status))

        for task, status in ready_to_be_removed:
            self.tasks_to_remove.remove((task, status))
            self.remove_task(task, status)



