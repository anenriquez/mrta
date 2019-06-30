import uuid
import time
import logging
import logging.config
from allocation.utils.config_logger import config_logger
from allocation.utils.uuid import generate_uuid


class AllocationRequester(object):

    def __init__(self, api):

        self.api = api
        self.api.add_callback(self, 'DONE', 'done_cb')

        config_logger('../config/logging.yaml')
        self.logger = logging.getLogger('task_requester')

    def request_allocation(self, tasks):
        allocation_request_msg = dict()
        allocation_request_msg['header'] = dict()
        allocation_request_msg['payload'] = dict()
        allocation_request_msg['header']['type'] = 'ALLOCATION-REQUEST'
        allocation_request_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        allocation_request_msg['header']['msgId'] = generate_uuid()
        allocation_request_msg['header']['timestamp'] = int(round(time.time()) * 1000)
        allocation_request_msg['payload']['metamodel'] = 'ropod-msg-schema.json'
        allocation_request_msg['payload']['tasks'] = dict()

        for task in tasks:
            allocation_request_msg['payload']['tasks'][task.id] = task.to_dict()

        self.logger.debug("AllocationRequester request allocation of tasks %s", [task.id for task in tasks])

        self.api.shout(allocation_request_msg, 'TASK-ALLOCATION')

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
