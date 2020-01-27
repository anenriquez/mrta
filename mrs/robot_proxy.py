import argparse
import logging.config

from fmlib.models.robot import Robot as RobotModel
from planner.planner import Planner
from ropod.structs.task import TaskStatus as TaskStatusConst
from stn.exceptions.stp import NoSTPSolution

from mrs.allocation.bidder import Bidder
from mrs.config.configurator import Configurator
from mrs.db.models.task import Task
from mrs.execution.delay_recovery import DelayRecovery
from mrs.messages.assignment_update import AssignmentUpdate
from mrs.messages.task_status import TaskStatus
from mrs.simulation.simulator import Simulator, SimulatorInterface
from mrs.timetable.timetable import Timetable

_component_modules = {'simulator': Simulator,
                      'timetable': Timetable,
                      'bidder': Bidder,
                      'planner': Planner,
                      'delay_recovery': DelayRecovery}


class RobotProxy:
    def __init__(self, robot_id, api, robot_proxy_store, bidder, delay_recovery, **kwargs):
        self.logger = logging.getLogger('mrs.robot.proxy%s' % robot_id)

        self.robot_id = robot_id
        self.api = api
        self.robot_proxy_store = robot_proxy_store
        self.bidder = bidder
        self.robot_model = RobotModel.create_new(robot_id)
        self.recovery_method = delay_recovery.method
        self.simulator_interface = SimulatorInterface(kwargs.get('simulator'))

        self.api.register_callbacks(self)
        self.logger.info("Initialized RobotProxy %s", robot_id)

    def task_cb(self, msg):
        payload = msg['payload']
        task = Task.from_payload(payload)
        if self.robot_id in task.assigned_robots:
            self.logger.critical("Received task %s", task.task_id)
            task.freeze()

    def task_status_cb(self, msg):
        payload = msg['payload']
        task_status = TaskStatus.from_payload(payload)
        if task_status.robot_id == self.robot_id:
            self.logger.debug("Received task status % for task %s ", task_status.status, task_status.task_id)
            task = Task.get_task(task_status.task_id)

            if task_status.status in [TaskStatusConst.COMPLETED, TaskStatusConst.CANCELED, TaskStatusConst.ABORTED]:
                self.bidder.remove_task(task)
                task.update_status(task_status.status)

            elif task_status.status == TaskStatusConst.UNALLOCATED:
                self.re_allocate(task)

            else:
                task.update_status(task_status.status)

    def re_allocate(self, task):
        self.logger.warning("Re-allocating task %s", task.task_id)
        self.bidder.remove_task(task)
        task.update_status(TaskStatusConst.UNALLOCATED)

    def robot_pose_cb(self, msg):
        payload = msg.get("payload")
        self.logger.debug("Robot %s received pose", self.robot_id)
        self.robot_model.update_position(**payload.get("pose"))

    def assignment_update_cb(self, msg):
        payload = msg['payload']
        assignment_update = AssignmentUpdate.from_payload(payload)
        self.logger.debug("Assignment Update received")
        stn = self.bidder.timetable.stn

        for a in assignment_update.assignments:
            stn.assign_timepoint(a.assigned_time, a.task_id, a.node_type, force=True)
            stn.execute_timepoint(a.task_id, a.node_type)
            stn.execute_incoming_edge(a.task_id, a.node_type)
            stn.remove_old_timepoints()

        last_assignment = assignment_update.assignments.pop()
        last_executed_task = Task.get_task(last_assignment.task_id)

        self.logger.debug("Updated STN: %s", stn)
        self.bidder.timetable.stn = stn
        self.bidder.timetable.store()

        try:
            dispatchable_graph = self.bidder.timetable.compute_dispatchable_graph(stn)
            self.logger.debug("Updated DispatchableGraph %s: ", dispatchable_graph)
            self.bidder.timetable.dispatchable_graph = dispatchable_graph
        except NoSTPSolution:
            self.logger.warning("Temporal network becomes inconsistent")
            next_task = self.bidder.timetable.get_next_task(last_executed_task)
            if next_task:
                self.recover(next_task)

        self.bidder.timetable.store()

    def recover(self, task):
        if self.recovery_method.name.endswith("abort"):
            self.logger.warning("Aborting allocation of task %s", task.task_id)
            task.update_status(TaskStatusConst.ABORTED)
            self.bidder.remove_task(task)

        elif self.recovery_method.name.endswith("re-allocate"):
            self.re_allocate(task)

    def run(self):
        try:
            self.api.start()
            while True:
                self.simulator_interface.run()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.robot_id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('robot_id', type=str, help='example: robot_001')
    args = parser.parse_args()

    config = Configurator(args.file, component_modules=_component_modules)
    components = config.config_robot_proxy(args.robot_id)

    robot = RobotProxy(**components)
    robot.run()
