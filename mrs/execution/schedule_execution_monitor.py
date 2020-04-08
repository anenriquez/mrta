import logging

from fmlib.models.tasks import TransportationTask as Task
from mrs.exceptions.execution import InconsistentAssignment
from mrs.messages.d_graph_update import DGraphUpdate
from mrs.messages.task_status import TaskStatus
from mrs.utils.time import relative_to_ztp
from ropod.structs.status import ActionStatus as ActionStatusConst, TaskStatus as TaskStatusConst
from ropod.utils.timestamp import TimeStamp
from stn.exceptions.stp import NoSTPSolution
import uuid


class ScheduleExecutionMonitor:

    def __init__(self, robot_id, timetable, delay_recovery, **kwargs):
        """ Includes methods to monitor the schedule of a robot's allocated tasks
        """
        self.robot_id = robot_id
        self.timetable = timetable
        self.timetable.fetch()
        self.recovery_method = delay_recovery.method
        self.api = kwargs.get("api")

        self.d_graph_update_received = False
        self.current_task = None
        self.last_task = None

        self.logger = logging.getLogger('mrs.schedule.monitor.%s' % self.robot_id)
        self.logger.debug("ScheduleMonitor initialized %s", self.robot_id)

    def configure(self, **kwargs):
        api = kwargs.get('api')
        if api:
            self.api = api

    def d_graph_update_cb(self, msg):
        payload = msg['payload']
        self.logger.critical("Received DGraph update")
        d_graph_update = DGraphUpdate.from_payload(payload)
        d_graph_update.update_timetable(self.timetable, self.last_task)
        self.logger.debug("STN update %s", self.timetable.stn)
        self.logger.debug("Dispatchable graph update %s", self.timetable.dispatchable_graph)
        self.d_graph_update_received = True

    def task_status_cb(self, msg):
        payload = msg['payload']
        timestamp = TimeStamp.from_str(msg["header"]["timestamp"]).to_datetime()
        task_status = TaskStatus.from_payload(payload)

        task = Task.get_task(task_status.task_id)
        self.logger.critical("Received task status message for task %s", task.task_id)

        if task_status.task_status == TaskStatusConst.ONGOING:
            self.update_timetable(task, task_status.task_progress, timestamp)

        elif task_status.task_status == TaskStatusConst.COMPLETED:
            self.logger.debug("Completing execution of task %s", task.task_id)
            self.last_task = self.current_task
            self.current_task = None
            if "re-schedule" in self.recovery_method.name:
                self.re_schedule(task)

        self.logger.critical("Sending task status %s for task %s", task_status.task_status, task.task_id)
        self.api.publish(msg, groups=["TASK-ALLOCATION"])
        task.update_status(task_status.task_status)

    def update_timetable(self, task, task_progress, timestamp):
        self.logger.debug("Updating timetable")

        r_assigned_time = relative_to_ztp(self.timetable.ztp, timestamp)
        first_action_id = task.plan[0].actions[0].action_id

        if task_progress.action_id == first_action_id and \
                task_progress.action_status.status == ActionStatusConst.ONGOING:
            node_id, node = self.timetable.stn.get_node_by_type(task.task_id, 'start')
            is_consistent = self.update_timepoint(r_assigned_time, node, node_id)
            self.recover(task, task_progress, r_assigned_time, is_consistent)
        else:
            # An action could be associated to two nodes, e.g., between pickup and delivery there is only one action
            nodes = self.timetable.stn.get_nodes_by_action(task_progress.action_id)

            for node_id, node in nodes:
                if (node.node_type == 'pickup' and
                    task_progress.action_status.status == ActionStatusConst.ONGOING) or\
                        (node.node_type == 'delivery' and
                         task_progress.action_status.status == ActionStatusConst.COMPLETED):

                    if task.task_id == uuid.UUID("45b34703-eaaf-4063-b3cc-15acb7e850ca") and node.node_type == 'delivery':
                        r_assigned_time = 29615.0

                    is_consistent = self.update_timepoint(r_assigned_time, node, node_id)
                    self.recover(task, task_progress, r_assigned_time, is_consistent)

    def update_timepoint(self, r_assigned_time, node, node_id):
        is_consistent = True
        self.logger.debug("Assigning time %s to task %s timepoint %s", r_assigned_time, node.task_id,
                          node.node_type)
        try:
            self.timetable.assign_timepoint(r_assigned_time, node_id)

        except InconsistentAssignment as e:
            self.logger.warning("Assignment of time %s to task %s node_type %s is inconsistent "
                                "Assigning anyway.. ", e.assigned_time, e.task_id, e.node_type)
            self.timetable.stn.assign_timepoint(e.assigned_time, node_id, force=True)
            is_consistent = False

        self.timetable.stn.execute_timepoint(node_id)
        self.logger.debug("STN: \n %s",  self.timetable.stn)
        return is_consistent

    def _re_compute_dispatchable_graph(self):
        self.logger.debug("Recomputing dispatchable graph ")
        try:
            self.timetable.dispatchable_graph = self.timetable.compute_dispatchable_graph(self.timetable.stn)
            self.logger.debug("Dispatchable graph robot %s: %s", self.timetable.robot_id, self.timetable.dispatchable_graph)
        except NoSTPSolution:
            self.logger.warning("Temporal network is inconsistent")
            self.logger.debug("STN: %s", self.timetable.stn)
            self.logger.debug("Dispatchable graph: %s", self.timetable.dispatchable_graph)

    def recover(self, task, task_progress, r_assigned_time, is_consistent):
        """ Applies a recovery method (preventive or corrective) if needed.
        A preventive recovery prevents delay of next_task. Applied BEFORE current task becomes inconsistent
        A corrective recovery prevents delay of next task. Applied AFTER current task becomes inconsistent

        task (Task) : task
        is_consistent (boolean): True if the last assignment was consistent, false otherwise
        """
        tasks_to_recover = self.recovery_method.recover(self.timetable, task, task_progress, r_assigned_time, is_consistent)

        # if "re-schedule" in self.recovery_method.name:
        #     self.recover_tasks(tasks_to_recover)
        #     self._re_compute_dispatchable_graph()
        #     self.re_schedule(task)

        for task in tasks_to_recover:
            if "re-allocate" in self.recovery_method.name:
                self.re_allocate(task)
            elif "abort" in self.recovery_method.name:
                self.abort(task)

    # def recover_tasks(self, tasks_to_recover):
    #     for task in tasks_to_recover:
    #         if "re-allocate" in self.recovery_method.name:
    #             self.re_allocate(task)
    #         elif "abort" in self.recovery_method.name:
    #             self.abort(task)

    def re_allocate(self, task):
        self.logger.critical("Triggering re-allocation of task %s", task.task_id)
        task.update_status(TaskStatusConst.UNALLOCATED)
        self.timetable.remove_task(task.task_id)
        task_status = TaskStatus(task.task_id, self.robot_id, TaskStatusConst.UNALLOCATED)
        self.send_task_status(task_status)

    def abort(self, task):
        self.logger.debug("Trigger abortion of task %s", task.task_id)
        task.update_status(TaskStatusConst.ABORTED)
        self.timetable.remove_task(task.task_id)
        task_status = TaskStatus(task.task_id, self.robot_id, TaskStatusConst.ABORTED)
        self.send_task_status(task_status)

    def re_schedule(self, task):
        self.logger.debug("Trigger rescheduling")
        task_status = TaskStatus(task.task_id, self.robot_id, TaskStatusConst.RE_SCHEDULING)
        self.send_task_status(task_status)

    def send_task_status(self, task_status):
        self.logger.debug("Sending task status for task %s", task_status.task_id)
        msg = self.api.create_message(task_status)
        self.api.publish(msg, groups=["TASK-ALLOCATION"])
