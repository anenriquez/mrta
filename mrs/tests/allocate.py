import argparse
import json
import logging.config
import time

from fmlib.db.mongo import MongoStore
from fmlib.db.mongo import MongoStoreInterface
from fmlib.models.tasks import TaskStatus
from fmlib.utils.utils import load_file_from_module, load_yaml
from importlib_resources import open_text
from mrs.config.params import ConfigParams
from mrs.db.models.task import Task
from mrs.messages.task_contract import TaskContract
from mrs.messages.task_progress import TaskProgress
from mrs.simulation.simulator import Simulator, SimulatorInterface
from mrs.utils.datasets import load_tasks_to_db
from mrs.utils.utils import load_yaml_file
from pymodm.context_managers import switch_collection
from ropod.pyre_communicator.base_class import RopodPyre
from ropod.structs.task import TaskStatus as TaskStatusConst


def get_msg_fixture(msg_file):
    msg_module = 'mrs.tests.messages'

    with open_text(msg_module, msg_file) as json_msg:
        msg = json.load(json_msg)

    return msg


class AllocationTest(RopodPyre):
    def __init__(self, test_case, config_file=None):
        zyre_config = {'node_name': 'allocation_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['START-TEST',
                                         'ALLOCATION']}

        super().__init__(zyre_config, acknowledge=False)

        if config_file is None:
            self._config_params = ConfigParams.default()
        else:
            self._config_params = ConfigParams.from_file(config_file)

        self._config_params.update(**test_case)

        self.logger = logging.getLogger('mrs.allocate')
        logger_config = self._config_params.get('logger')
        logging.config.dictConfig(logger_config)

        simulator = Simulator(**self._config_params.get("simulator"))
        self.simulator_interface = SimulatorInterface(simulator)

        self.tasks = list()
        self.allocations = dict()
        self.terminated = False
        self.clean_stores()

        self.logger.info("Initialized AllocationTest: %s", test_case.get("description"))

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

    def setup(self, robot_poses_file):
        robot_poses = load_yaml_file(robot_poses_file)
        msg = get_msg_fixture('robot_pose.json')
        for robot_id, pose in robot_poses.items():
            msg['payload']['robotId'] = robot_id
            msg['payload']['pose'] = pose
            self.whisper(msg, peer=robot_id + "_proxy")
            self.logger.info("Send init pose to %s: ", robot_id)

    def load_tasks(self, dataset_module, dataset_name, **kwargs):
        sim_config = self._config_params.get('simulator')
        if sim_config:
            self.tasks = load_tasks_to_db(dataset_module, dataset_name, initial_time=sim_config.get('initial_time'))
        else:
            self.tasks = load_tasks_to_db(dataset_module, dataset_name)

    def trigger(self):
        msg = get_msg_fixture('start_test.json')
        self.shout(msg)
        self.logger.info("Test triggered")
        self.simulator_interface.start()

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

        if msg_type == 'TASK-PROGRESS':
            progress = TaskProgress.from_payload(payload)
            self.logger.debug("Task progress received: %s", progress)

    def check_termination_test(self):
        with switch_collection(TaskStatus, TaskStatus.Meta.archive_collection):
            completed_tasks = Task.get_tasks_by_status(TaskStatusConst.COMPLETED)
            canceled_tasks = Task.get_tasks_by_status(TaskStatusConst.CANCELED)
            aborted_tasks = Task.get_tasks_by_status(TaskStatusConst.ABORTED)

            self.logger.info("Number of completed tasks: %s ", len(completed_tasks))
            self.logger.info("Number of canceled tasks: %s", len(canceled_tasks))
            self.logger.info("Number of aborted tasks: %s", len(aborted_tasks))

            tasks = completed_tasks + canceled_tasks + aborted_tasks

            if len(tasks) == len(self.tasks):
                self.logger.info("Terminating test")
                self.logger.info("Allocations: %s", self.allocations)
                self.terminated = True

    def terminate(self):
        print("Exiting test...")
        self.simulator_interface.stop()
        test.shutdown()
        print("Test terminated")

    def run(self):
        try:
            test.start()
            time.sleep(10)
            test.setup(args.robot_poses_file)
            time.sleep(10)
            test.trigger()
            while not test.terminated:
                print("Approx current time: ", self.simulator_interface.get_current_time())
                test.check_termination_test()
                time.sleep(0.5)

            self.terminate()

        except (KeyboardInterrupt, SystemExit):
            print('Task request test interrupted; exiting')
            self.terminate()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('--case', type=int, action='store', default=1, help='Test case number')
    parser.add_argument('--dataset_module', type=str, action='store', help='Dataset module',
                        default='mrs.tests.datasets')
    parser.add_argument('--dataset_name', type=str, action='store', help='Dataset name',
                        default='non_overlapping')
    parser.add_argument('--robot_poses_file', type=str, action='store', help='Path to robot init poses file',
                        default='robot_init_poses.yaml')
    args = parser.parse_args()

    case = args.case

    test_cases = load_file_from_module('mrs.tests.cases', 'test-cases.yaml')
    test_config = {case: load_yaml(test_cases).get(case)}
    test_case = test_config.popitem()[1]

    test = AllocationTest(test_case, args.file)
    test.load_tasks(args.dataset_module, args.dataset_name)
    test.run()
