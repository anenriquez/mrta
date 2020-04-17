import logging.config
import logging.config
import time

from fmlib.db.mongo import MongoStore
from fmlib.db.mongo import MongoStoreInterface
from fmlib.models.tasks import TaskStatus
from pymodm.context_managers import switch_collection
from ropod.pyre_communicator.base_class import RopodPyre
from ropod.structs.task import TaskStatus as TaskStatusConst

from fmlib.models.tasks import TransportationTask as Task
from mrs.messages.task_contract import TaskContract
from mrs.simulation.simulator import Simulator, SimulatorInterface
from mrs.utils.datasets import load_tasks_to_db
from mrs.utils.utils import get_msg_fixture


class Allocate(RopodPyre):
    def __init__(self, config_params, robot_poses, dataset_module, dataset_name):
        zyre_config = {'node_name': 'allocation_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['START-TEST',
                                         'ALLOCATION']}

        super().__init__(zyre_config, acknowledge=False)

        self._config_params = config_params
        self._robot_poses = robot_poses
        self._dataset_module = dataset_module
        self._dataset_name = dataset_name

        self.logger = logging.getLogger('mrs.allocate')
        logger_config = self._config_params.get('logger')
        logging.config.dictConfig(logger_config)

        simulator = Simulator(**self._config_params.get("simulator"))
        self.simulator_interface = SimulatorInterface(simulator)

        self.allocations = dict()
        self.terminated = False
        self.clean_stores()
        self.tasks = self.load_tasks()

    def clean_store(self, store):
        store_interface = MongoStoreInterface(store)
        store_interface.clean()
        self.logger.info("Store %s cleaned", store_interface._store.db_name)

    def clean_stores(self):
        fleet = self._config_params.get('fleet')
        robot_proxy_store_config = self._config_params.get("robot_proxy_store")
        robot_store_config = self._config_params.get("robot_store")
        store_configs = {'robot_proxy_store': robot_proxy_store_config,
                         'robot_store': robot_store_config}

        for robot_id in fleet:
            for store_name, config in store_configs.items():
                config.update({'db_name': store_name + '_' + robot_id.split('_')[1]})
                store = MongoStore(**config)
                self.clean_store(store)

        ccu_store_config = self._config_params.get('ccu_store')
        store = MongoStore(**ccu_store_config)
        self.clean_store(store)

    def send_robot_positions(self):
        msg = get_msg_fixture('robot_pose.json')
        fleet = self._config_params.get("fleet")
        for robot_id in fleet:
            pose = self._robot_poses.get(robot_id)
            msg['payload']['robotId'] = robot_id
            msg['payload']['pose'] = pose
            self.shout(msg)
            self.logger.info("Send init pose to %s: ", robot_id)

    def load_tasks(self):
        sim_config = self._config_params.get('simulator')
        if sim_config:
            tasks = load_tasks_to_db(self._dataset_module, self._dataset_name, initial_time=sim_config.get('initial_time'))
        else:
            tasks = load_tasks_to_db(self._dataset_module, self._dataset_name)
        return tasks

    def trigger(self):
        msg = get_msg_fixture('start_test.json')
        self.shout(msg)
        self.logger.info("Test triggered")
        self.simulator_interface.start(msg["payload"]["initial_time"])

    def receive_msg_cb(self, msg_content):
        msg = self.convert_zyre_msg_to_dict(msg_content)
        if msg is None:
            return
        msg_type = msg['header']['type']
        payload = msg['payload']

        if msg_type == 'TASK-CONTRACT':
            task_contract = TaskContract.from_payload(payload)
            self.allocations[task_contract.task_id] = task_contract.robot_id
            self.logger.debug("Allocation: (%s, %s)", task_contract.task_id, task_contract.robot_id)

    def check_termination_test(self):
        unallocated_tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        allocated_tasks = Task.get_tasks_by_status(TaskStatusConst.ALLOCATED)
        preempted_tasks = Task.get_tasks_by_status(TaskStatusConst.PREEMPTED)
        planned_tasks = Task.get_tasks_by_status(TaskStatusConst.PLANNED)
        dispatched_tasks = Task.get_tasks_by_status(TaskStatusConst.DISPATCHED)
        ongoing_tasks = Task.get_tasks_by_status(TaskStatusConst.ONGOING)

        with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
            completed_tasks = Task.get_tasks_by_status(TaskStatusConst.COMPLETED)
            canceled_tasks = Task.get_tasks_by_status(TaskStatusConst.CANCELED)
            aborted_tasks = Task.get_tasks_by_status(TaskStatusConst.ABORTED)

        self.logger.info("Unallocated: %s", len(unallocated_tasks))
        self.logger.info("Allocated: %s", len(allocated_tasks))
        self.logger.info("Planned: %s ", len(planned_tasks))
        self.logger.info("Dispatched: %s", len(dispatched_tasks))
        self.logger.info("Ongoing: %s", len(ongoing_tasks))
        self.logger.info("Completed: %s ", len(completed_tasks))
        self.logger.info("Preempted: %s ", len(preempted_tasks))
        self.logger.info("Canceled: %s", len(canceled_tasks))
        self.logger.info("Aborted: %s", len(aborted_tasks))

        tasks = completed_tasks + preempted_tasks

        if len(tasks) == len(self.tasks):
            self.logger.info("Terminating test")
            self.logger.info("Allocations: %s", self.allocations)
            self.terminated = True

    def terminate(self):
        print("Exiting test...")
        self.simulator_interface.stop()
        self.shutdown()
        print("Test terminated")

    def start_allocation(self):
        self.start()
        time.sleep(10)
        self.send_robot_positions()
        time.sleep(10)
        self.trigger()

    def run(self):
        try:
            self.start_allocation()
            while not self.terminated:
                print("Approx current time: ", self.simulator_interface.get_current_time())
                self.check_termination_test()
                time.sleep(0.5)
            self.terminate()

        except (KeyboardInterrupt, SystemExit):
            print('Task request test interrupted; exiting')
            self.terminate()
