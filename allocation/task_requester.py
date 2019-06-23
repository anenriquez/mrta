import yaml
import uuid
import time
import logging
import logging.config
from allocation.config.dataset_loader import DatasetLoader


class TaskRequester(object):

    def __init__(self, api):

        self.api = api
        self.api.add_callback(self, 'DONE', 'done_cb')
        self.dataset_loader = DatasetLoader()

        with open('../config/logging.yaml', 'r') as f:
            config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)

        self.logger = logging.getLogger('task_allocator')

    def allocate_dataset(self, dataset_id):
        dataset = self.dataset_loader.read_dataset(dataset_id)
        start_time = dataset['start_time']
        dataset_id = dataset['dataset_id']
        self.logger.info("Dataset: %s", dataset_id)
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
        self.api.shout(start_msg, 'TASK-ALLOCATION')

    def send_terminate_msg(self):
        terminate_msg = dict()
        terminate_msg['header'] = dict()
        terminate_msg['payload'] = dict()
        terminate_msg['header']['type'] = 'TERMINATE'
        terminate_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        terminate_msg['header']['msgId'] = str(uuid.uuid4())
        terminate_msg['header']['timestamp'] = int(round(time.time()) * 1000)
        self.api.shout(terminate_msg, 'TASK-ALLOCATION')
        self.api.terminated = True

    def done_cb(self, msg):
        self.logger.debug("Received done msg")
        self.send_terminate_msg()
