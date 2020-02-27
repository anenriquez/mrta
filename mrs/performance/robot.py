import logging

from mrs.db.models.performance.robot import RobotPerformance


class RobotPerformanceTracker:
    def __init__(self):
        self.logger = logging.getLogger("mrs.performance.robot.tracker")
        self.processed_tasks = list()

    def update_metrics(self, robot_id, tasks_progress):
        self.logger.debug("Updating performance of robot %s", robot_id)
        robot_performance = RobotPerformance.get_robot_performance(robot_id)
        for task_idx, actions_progress in enumerate(tasks_progress):
            task_id = actions_progress[0].action.task_id
            if task_id not in self.processed_tasks:
                robot_performance.update_allocated_tasks(task_id)
                for action_progress in actions_progress:
                    time_ = (action_progress.finish_time - action_progress.start_time).total_seconds()
                    if action_progress.action.type == "ROBOT-TO-PICKUP":
                        robot_performance.update_travel_time(time_)

                        if task_idx > 0:
                            prev_delivery_time = tasks_progress[task_idx-1][-1].finish_time
                            start_time = tasks_progress[task_idx][0].start_time
                            idle_time = (start_time - prev_delivery_time).total_seconds()
                            robot_performance.update_idle_time(idle_time)

                    elif action_progress.action.type == "PICKUP-TO-DELIVERY":
                        robot_performance.update_work_time(time_)

                self.processed_tasks.append(task_id)

        start_first_task, finish_last_task = self.get_start_finish_times(tasks_progress)
        total_time = (finish_last_task - start_first_task).total_seconds()

        robot_performance.update_total_time(total_time)
        robot_performance.update_makespan(finish_last_task)

    @staticmethod
    def get_start_finish_times(tasks_progress):
        finish_last_task = tasks_progress[-1][-1].finish_time
        start_fist_task = tasks_progress[0][0].start_time
        return start_fist_task, finish_last_task

