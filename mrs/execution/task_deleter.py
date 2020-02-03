import logging

from mrs.messages.remove_task import RemoveTask


class TaskDeleter:
    def __init__(self, auctioneer, dispatcher, timetable_manager, **kwargs):
        self.auctioneer = auctioneer
        self.dispatcher = dispatcher
        self.timetable_manager = timetable_manager

        self.api = kwargs.get('api')
        self.logger = logging.getLogger("mrs.task.deleter")

    def remove_task(self, task, status):
        self.logger.critical("Deleting task %s from timetable and changing its status to %s", task.task_id, status)
        for robot_id in task.assigned_robots:
            timetable = self.timetable_manager.get_timetable(robot_id)
            timetable.remove_task(task.task_id)
            self.auctioneer.deleted_a_task.append(robot_id)
            # TODO: Send d_graph_update only if the deleted task was in the previous update
            self.dispatcher.send_d_graph_update(robot_id)
            self.send_remove_task(task.task_id, status, robot_id)
            task.update_status(status)

            self.logger.debug("STN robot %s: %s", robot_id, timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", robot_id, timetable.dispatchable_graph)

    def send_remove_task(self, task_id, status, robot_id):
        remove_task = RemoveTask(task_id, status)
        msg = self.api.create_message(remove_task)
        self.api.publish(msg, peer=robot_id + '_proxy')
