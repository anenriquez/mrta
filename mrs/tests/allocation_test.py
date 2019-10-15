import logging.config

from ropod.pyre_communicator.base_class import RopodPyre
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid


class Allocate(RopodPyre):
    def __init__(self, tasks, logger_config):
        zyre_config = {'node_name': 'allocation_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['START-TEST',
                                         'ALLOCATION',
                                         'NO-ALLOCATION']}

        super().__init__(zyre_config, acknowledge=False)

        self.logger = logging.getLogger('mrs.allocate')
        logging.config.dictConfig(logger_config)

        self.tasks = tasks
        self.n_received_msgs = 0
        self.terminated = False

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

        if msg_type == 'ALLOCATION' or msg_type == 'NO-ALLOCATION':
            self.n_received_msgs += 1
            self.logger.debug("Messages received: %s", self.n_received_msgs)
            self.check_termination_test()

    def check_termination_test(self):
        print("Checking termination test")
        if self.n_received_msgs == len(self.tasks):
            logging.info("Terminating test")
            self.terminated = True

