import logging.config
import time
import argparse

from fmlib.db.mongo import MongoStore
from fmlib.db.mongo import MongoStoreInterface
from mrs.tests.fixtures.utils import get_msg_fixture
from mrs.utils.datasets import load_tasks_to_db
from mrs.utils.utils import load_yaml_file
from ropod.pyre_communicator.base_class import RopodPyre
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid
from mrs.config.configurator import Configurator


class AllocationTest(RopodPyre):
    def __init__(self, config_file=None):
        zyre_config = {'node_name': 'allocation_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['START-TEST',
                                         'ALLOCATION']}

        super().__init__(zyre_config, acknowledge=False)

        self.config_params = Configurator(config_file).config_params
        self.logger = logging.getLogger('mrs.allocate')

        self.tasks = list()
        self.n_received_msgs = 0
        self.terminated = False
        self.clean_stores()

        self.logger.info("Initialized AllocationTest")

    def clean_store(self, store):
        store_interface = MongoStoreInterface(store)
        store_interface.clean()
        self.logger.info("Store %s cleaned", store_interface._store.db_name)

    def clean_stores(self):
        fleet = self.config_params.get('fleet')
        robot_store_config = self.config_params.get("robot_store")

        for robot_id in fleet:
            robot_store_config.update({'db_name': 'robot_store_' + robot_id.split('_')[1]})
            store = MongoStore(**robot_store_config)
            self.clean_store(store)

        ccu_store_config = self.config_params.get('ccu_store')
        store = MongoStore(**ccu_store_config)
        self.clean_store(store)

    def setup(self, robot_poses_file):
        robot_poses = load_yaml_file(robot_poses_file)
        msg = get_msg_fixture('robot_pose.json')
        for robot_id, pose in robot_poses.items():
            msg['payload']['robotId'] = robot_id
            msg['payload']['pose'] = pose
            self.whisper(msg, peer=robot_id)
            self.logger.info("Send init pose to %s: ", robot_id)

    def load_tasks(self, dataset_module, dataset_name, **kwargs):
        self.tasks = load_tasks_to_db(dataset_module, dataset_name, **kwargs)

    def trigger(self):
        test_msg = dict()
        test_msg['header'] = dict()
        test_msg['payload'] = dict()
        test_msg['header']['type'] = 'START-TEST'
        test_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        test_msg['header']['msgId'] = generate_uuid()
        test_msg['header']['timestamp'] = TimeStamp().to_str()

        test_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'

        self.shout(test_msg)
        self.logger.info("Test triggered")

    def receive_msg_cb(self, msg_content):
        msg = self.convert_zyre_msg_to_dict(msg_content)
        if msg is None:
            return
        msg_type = msg['header']['type']

        if msg_type == 'TASK-CONTRACT':
            self.n_received_msgs += 1
            self.logger.debug("Messages received: %s", self.n_received_msgs)
            self.check_termination_test()

    def check_termination_test(self):
        print("Checking termination test")
        if self.n_received_msgs == len(self.tasks):
            logging.info("Terminating test")
            self.terminated = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')
    parser.add_argument('--dataset_module', type=str, action='store', help='Dataset module',
                        default='mrs.tests.fixtures.datasets')
    parser.add_argument('--dataset_name', type=str, action='store', help='Dataset name',
                        default='overlapping')
    parser.add_argument('--robot_poses_file', type=str, action='store', help='Path to robot init poses file',
                        default='fixtures/robot_init_poses.yaml')
    args = parser.parse_args()

    test = AllocationTest(args.file)
    test.load_tasks(args.dataset_module, args.dataset_name)

    try:
        time.sleep(40)
        test.start()
        time.sleep(10)
        test.setup(args.robot_poses_file)
        test.trigger()
        while not test.terminated:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        print('Task request test interrupted; exiting')

    print("Exiting test...")
    test.shutdown()
