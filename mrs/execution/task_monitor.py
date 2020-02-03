import logging

from fmlib.models.actions import Action
from mrs.db.models.task import Task
from mrs.messages.task_progress import TaskProgress
from mrs.simulation.simulator import SimulatorInterface
from ropod.structs.status import TaskStatus as TaskStatusConst
from ropod.utils.timestamp import TimeStamp


class TaskMonitor(SimulatorInterface):
    def __init__(self, timetable_manager, **kwargs):
        simulator = kwargs.get('simulator')
        super().__init__(simulator)

        self.timetable_manager = timetable_manager
        self.tasks_to_remove = list()

        self.logger = logging.getLogger("mrs.task.monitor")

    def task_progress_cb(self, msg):
        payload = msg['payload']
        progress = TaskProgress.from_payload(payload)
        self.logger.critical("Task %s, status %s ", progress.task_id, progress.status)

        task = Task.get_task(progress.task_id)
        action_progress = progress.action_progress

        self._update_task_progress(task, action_progress)
        self._update_task_schedule(task, action_progress)
        self._update_timetables(task, action_progress)

        if progress.status == TaskStatusConst.COMPLETED:
            self.tasks_to_remove.append((task, progress.status))

        elif progress.status in [TaskStatusConst.COMPLETED, TaskStatusConst.CANCELED, TaskStatusConst.ABORTED]:
            self.remove_task(task, progress.status)
        else:
            task.update_status(progress.task_status)

    def _update_task_progress(self, task, action_progress):
        self.logger.critical("Updating task progress of task %s", task.task_id)
        task.update_progress(action_progress.action_id,
                             action_progress.status)

    def _update_timetables(self, task, action_progress):
        for robot_id in task.assigned_robots:
            timetable = self.timetable_manager.get_timetable(robot_id)
            self._update_timetable(task.task_id, timetable, action_progress)

    def _update_timetable(self, task_id, timetable, action_progress):
        action = Action.get_action(action_progress.action_id)
        start_node, finish_node = action.get_node_names()
        if action_progress.start_time:
            self._assign_time(action_progress.start_time, timetable, task_id, start_node)
        if action_progress.finish_time:
            self._assign_time(action_progress.finish_time, timetable, task_id, finish_node)

    def _assign_time(self, absolute_time, timetable, task_id, node_type):
        r_time = TimeStamp.from_datetime(absolute_time).get_difference(self.timetable_manager.ztp).total_seconds()
        self.logger.debug("Absolute time: %s, "
                          "Relative time: %s", absolute_time, r_time)
        timetable.update_stn(r_time, task_id, node_type)

    @staticmethod
    def _update_task_schedule(task, action_progress):
        first_action = task.status.progress.actions[0]
        last_action = task.status.progress.actions[-1]

        if action_progress.action_id == first_action.action.action_id:
            print("Updating start time")
            print(action_progress.start_time)
            task.update_start_time(action_progress.start_time)

        elif action_progress.action_id == last_action.action.action_id:
            print("Updating finish time")
            print(action_progress.finish_time)
            task.update_finish_time(action_progress.finish_time)
        else:
            print("None of the above")

    def run(self):
        # TODO: Check how this works outside simulation
        ready_to_be_removed = list()
        for task, status in self.tasks_to_remove:
            if task.finish_time < self.get_current_time():
                ready_to_be_removed.append((task, status))

        for task, status in ready_to_be_removed:
            self.tasks_to_remove.remove((task, status))
            self.task_deleter.remove_task(task, status)


    # @staticmethod
    # def _update_task(task_id):
    #     task = Task.get_task(task_id)
    #     first_action = task.status.progress.actions[0]
    #     last_action = task.status.progress.actions[-1]
    #
    #     if first_action.start_time:
    #         task.update_start_time(first_action.start_time)
    #     if last_action.finish_time:
    #         task.update_finish_time(last_action.finish_time)
    #     return task




