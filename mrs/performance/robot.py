import logging

from mrs.db.models.performance.robot import RobotPerformance


class RobotPerformanceTracker:
    def __init__(self):
        self.logger = logging.getLogger("mrs.performance.robot.tracker")
        self.processed_tasks = list()

    def update_metrics(self, robot_id, tasks_status):
        self.logger.debug("Updating performance of robot %s", robot_id)
        robot_performance = RobotPerformance.get_robot_performance(robot_id)

        tasks = list(tasks_status.items())

        for i, (task_id, task_status) in enumerate(tasks_status.items()):
            if task_id not in self.processed_tasks:
                for action_progress in task_status.progress.actions:

                    time_ = (action_progress.finish_time - action_progress.start_time).total_seconds()

                    if action_progress.action.type == "ROBOT-TO-PICKUP":
                        robot_performance.update_travel_time(time_)

                        if i > 0:
                            previous_task_status = tasks[i-1][1]
                            prev_delivery_time = previous_task_status.progress.actions[-1].finish_time
                            start_time = action_progress.start_time
                            idle_time = (start_time - prev_delivery_time).total_seconds()
                            robot_performance.update_idle_time(idle_time)

                    elif action_progress.action.type == "PICKUP-TO-DELIVERY":
                        robot_performance.update_work_time(time_)

                self.processed_tasks.append(task_id)

        finish_last_task = tasks[-1][1].progress.actions[-1].finish_time
        start_first_task = tasks[0][1].progress.actions[0].start_time
        total_time = (finish_last_task - start_first_task).total_seconds()

        robot_performance.update_total_time(total_time)
        robot_performance.update_makespan(finish_last_task)

    def update_allocated_tasks(self, robot_id, task_id):
        robot_performance = RobotPerformance.get_robot_performance(robot_id)
        robot_performance.update_allocated_tasks(task_id)
        self.logger.debug("Robot %s allocated tasks: %s", robot_id, [task_id for task_id in robot_performance.allocated_tasks])

    def update_timetables(self, timetable):
        self.logger.debug("Updating timetable of robot %s", timetable.robot_id)
        robot_performance = RobotPerformance.get_robot_performance(timetable.robot_id)
        robot_performance.update_timetables(timetable)

    @staticmethod
    def update_re_allocations(task):
        for robot_id in task.assigned_robots:
            robot_performance = RobotPerformance.get_robot_performance(robot_id)
            robot_performance.unallocated(task.task_id)
