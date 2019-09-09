import logging
import time

from fleet_management.db.mongo import MongoStore
from ropod.pyre_communicator.base_class import RopodPyre
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid

from mrs.utils.datasets import load_yaml, load_yaml_dataset


class AllocationTest(RopodPyre):
    def __init__(self, fleet, dataset):
        zyre_config = {'node_name': 'allocation_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['START-TEST',
                                         'ALLOCATION',
                                         'NO-ALLOCATION']}

        super().__init__(zyre_config, acknowledge=False)

        robot_stores = self.get_fleet_db(fleet)
        ccu_store = MongoStore('ccu_store')
        stores = [ccu_store] + robot_stores
        self.clean_stores(stores)

        self.tasks = load_yaml_dataset(dataset)

        self.n_received_msgs = 0
        self.terminated = False

    @staticmethod
    def get_fleet_db(fleet):
        robot_stores = list()
        for robot_id in fleet:
            robot_stores.append(MongoStore('robot_' + robot_id.split('_')[1] + '_store'))

        return robot_stores

    @staticmethod
    def clean_stores(stores):
        for store in stores:
            print("Cleaning", store.db_name)
            # store.clean()

    def trigger(self):
        print("Test triggered")
        test_msg = dict()
        test_msg['header'] = dict()
        test_msg['payload'] = dict()
        test_msg['header']['type'] = 'START-TEST'
        test_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        test_msg['header']['msgId'] = generate_uuid()
        test_msg['header']['timestamp'] = TimeStamp().to_str()

        test_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'

        self.shout(test_msg)

    def receive_msg_cb(self, msg_content):
        msg = self.convert_zyre_msg_to_dict(msg_content)
        if msg is None:
            return
        msg_type = msg['header']['type']

        if msg_type == 'ALLOCATION' or msg_type == 'NO-ALLOCATION':
            self.logger.debug("Received message")
            self.n_received_msgs += 1
            self.check_termination_test()

    def check_termination_test(self):
        if self.n_received_msgs == len(self.tasks):
            logging.debug("Terminating test")
            self.terminated = True


if __name__ == '__main__':
    config_file = '../config/config.yaml'
    dataset = 'data/non_overlapping.yaml'

    config = load_yaml(config_file)
    fleet = config.get('resource_manager').get('resources').get('fleet')

    timeout_duration = 300  # 5 minutes

    test = AllocationTest(fleet, dataset)
    test.start()

    try:
        time.sleep(5)
        start_time = time.time()
        test.trigger()
        while not test.terminated and start_time + timeout_duration > time.time():
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        print('Task request test interrupted; exiting')

    print("Exiting test...")
    test.shutdown()



