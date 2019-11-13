import logging.config

from ropod.pyre_communicator.base_class import RopodPyre
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid
from mrs.utils.datasets import load_yaml, load_tasks_to_db
import time
from fmlib.db.mongo import MongoStore
from fmlib.db.mongo import MongoStoreInterface


class AllocationTest(RopodPyre):
    def __init__(self, config_params):
        zyre_config = {'node_name': 'allocation_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['START-TEST',
                                         'ALLOCATION']}

        super().__init__(zyre_config, acknowledge=False)

        self.config_params = config_params

        self.logger = logging.getLogger('mrs.allocate')
        logger_config = config.get('logger')
        logging.config.dictConfig(logger_config)

        self.tasks = list()
        self.n_received_msgs = 0
        self.terminated = False

        self.clean_stores()

    def clean_store(self, store):
        store_interface = MongoStoreInterface(store)
        store_interface.clean()
        self.logger.info("Store %s cleaned", store_interface._store.db_name)

    def clean_stores(self):
        fleet = self.config_params.get('resource_manager').get('resources').get('fleet')
        robot_store_config = self.config_params.get('robot_proxy').get("robot_store")

        for robot_id in fleet:
            robot_store_config.update({'db_name': 'robot_store_' + robot_id.split('_')[1]})
            store = MongoStore(**robot_store_config)
            self.clean_store(store)

        ccu_store_config = self.config_params.get('ccu_store')
        store = MongoStore(**ccu_store_config)
        self.clean_store(store)

    def load_tasks(self, dataset):
        self.tasks = load_tasks_to_db(dataset)

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

        if msg_type == 'ALLOCATION':
            self.n_received_msgs += 1
            self.logger.debug("Messages received: %s", self.n_received_msgs)
            self.check_termination_test()

    def check_termination_test(self):
        print("Checking termination test")
        if self.n_received_msgs == len(self.tasks):
            logging.info("Terminating test")
            self.terminated = True


if __name__ == '__main__':
    config_file = '../config/default/config.yaml'
    dataset = 'data/non_overlapping.yaml'

    config = load_yaml(config_file)
    test = AllocationTest(config)

    test.load_tasks(dataset)
    test.start()

    try:
        time.sleep(60)
        test.trigger()
        while not test.terminated:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        print('Task request test interrupted; exiting')

    print("Exiting test...")
    test.shutdown()
