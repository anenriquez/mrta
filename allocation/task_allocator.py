from allocation.auctioneer import Auctioneer
from ropod.pyre_communicator.base_class import RopodPyre
from allocation.config.config_file_reader import ConfigFileReader
import yaml
import uuid
import time
import os


class TaskAllocator(RopodPyre):
    def __init__(self, config_params):
        self.zyre_params = config_params.task_allocator_zyre_params
        super().__init__('task_allocator', self.zyre_params.groups, self.zyre_params.message_types)

    def read_dataset(self, dataset_id):
        my_dir = os.path.dirname(__file__)
        dataset_path = os.path.join(my_dir, 'datasets/' + dataset_id)

        with open(dataset_path, 'r') as file:
            dataset = yaml.safe_load(file)
        print("dataset: ", dataset)
        return dataset

    def allocate_dataset(self, dataset_id):
        dataset = self.read_dataset(dataset_id)
        start_time = dataset['start_time']
        dataset_id = dataset['dataset_id']
        self.send_start_msg(start_time, dataset_id)

    def send_start_msg(self, start_time, dataset_id):
        start_msg = dict()
        start_msg['header'] = dict()
        start_msg['payload'] = dict()
        start_msg['header']['type'] = 'START'
        start_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        start_msg['header']['msgId'] = str(uuid.uuid4())
        start_msg['header']['timestamp'] = int(round(time.time()) * 1000)
        start_msg['payload']['metamodel'] = 'ropod-msg-schema.json'
        start_msg['payload']['start_time'] = start_time
        start_msg['payload']['dataset_id'] = dataset_id
        self.shout(start_msg, 'TASK-ALLOCATION')

    def send_terminate_msg(self):
        terminate_msg = dict()
        terminate_msg['header'] = dict()
        terminate_msg['payload'] = dict()
        terminate_msg['header']['type'] = 'TERMINATE'
        terminate_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        terminate_msg['header']['msgId'] = str(uuid.uuid4())
        terminate_msg['header']['timestamp'] = int(round(time.time()) * 1000)
        self.shout(terminate_msg, 'TASK-ALLOCATION')
        self.terminated = True

    def receive_msg_cb(self, msg_content):
        dict_msg = self.convert_zyre_msg_to_dict(msg_content)
        if dict_msg is None:
            return
        message_type = dict_msg['header']['type']

        if message_type == 'DONE':
            self.send_terminate_msg()
