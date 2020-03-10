import copy
import logging
from datetime import timedelta

from mrs.simulation.simulator import SimulatorInterface
from pymodm.errors import DoesNotExist
from ropod.structs.task import TaskStatus as TaskStatusConst


class Dispatcher(SimulatorInterface):

    def __init__(self, stp_solver, timetable_manager, freeze_window, n_queued_tasks, planner, **kwargs):
        """ Dispatches tasks to a multi-robot system based on temporal constraints

        Args:

            stp_solver (STP): Simple Temporal Problem object
            timetable_manager (TimetableManager): contains the timetables of all the robots in the fleet
            freeze_window (float): Defines the time (minutes) within which a task can be scheduled
                        e.g, with a freeze window of 2 minutes, a task can be scheduled if its earliest
                        start navigation time is within the next 2 minutes.
            kwargs:
                api (API): object that provides middleware functionality
                robot_store (robot_store): interface to interact with the db
        """
        simulator = kwargs.get('simulator')
        super().__init__(simulator)

        self.logger = logging.getLogger('mrs.dispatcher')
        self.api = kwargs.get('api')
        self.ccu_store = kwargs.get('ccu_store')

        self.stp_solver = stp_solver
        self.timetable_manager = timetable_manager
        self.freeze_window = timedelta(minutes=freeze_window)
        self.n_queued_tasks = n_queued_tasks
        self.planner = planner

        self.robot_ids = list()
        self.d_graph_updates = dict()

        self.logger.debug("Dispatcher started")

    def configure(self, **kwargs):
        api = kwargs.get('api')
        ccu_store = kwargs.get('ccu_store')
        if api:
            self.api = api
        if ccu_store:
            self.ccu_store = ccu_store

    def register_robot(self, robot_id):
        self.logger.debug("Registering robot %s", robot_id)
        self.robot_ids.append(robot_id)

    def run(self):
        self.dispatch_tasks()

    def is_schedulable(self, start_time):
        current_time = self.get_current_timestamp()
        if start_time.get_difference(current_time) < self.freeze_window:
            return True
        return False

    def get_pre_task_action(self, task):
        travel_path = self.get_travel_path(task., task.request.pickup_location)
        travel_time = self.get_travel_time(travel_path)
        task.update_inter_timepoint_constraint(**travel_time.to_dict())

        # pre_task_action = GoTo(action_id=generate_uuid(),
        #                        type="ROBOT-TO-PICKUP",
        #                        locations=travel_path)
        # return travel_time

    def dispatch_tasks(self):
        for robot_id in self.robot_ids:
            timetable = self.timetable_manager.get_timetable(robot_id)
            try:
                task = timetable.get_earliest_task()
                if task and task.status.status == TaskStatusConst.PLANNED:
                    start_time = timetable.get_start_time(task.task_id)
                    if self.is_schedulable(start_time):
                        task.freeze()
                        self.dispatch_task(task, robot_id)
            except DoesNotExist:
                pass

    def dispatch_task(self, task, robot_id):
        """
        Sends a task to the appropriate robot in the fleet

        Args:
            task: a ropod.structs.task.Task object
            robot_id: a robot UUID
        """
        self.logger.debug("Dispatching task %s to robot %s", task.task_id, robot_id)
        task_msg = self.api.create_message(task)
        self.api.publish(task_msg)
        task.update_status(TaskStatusConst.DISPATCHED)

    def send_d_graph_update(self, robot_id):
        timetable = self.timetable_manager.get_timetable(robot_id)
        prev_d_graph_update = self.d_graph_updates.get(robot_id)
        d_graph_update = timetable.get_d_graph_update(self.n_queued_tasks)

        if prev_d_graph_update != d_graph_update:
            self.logger.debug("Sending DGraphUpdate to %s", robot_id)
            msg = self.api.create_message(d_graph_update)
            self.api.publish(msg, peer=robot_id)
            self.d_graph_updates[robot_id] = copy.deepcopy(d_graph_update)
