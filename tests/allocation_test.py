import logging
import time

from fleet_management.db.ccu_store import CCUStore
from ropod.pyre_communicator.base_class import RopodPyre
from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid

from mrs.db_interface import DBInterface
from mrs.utils.datasets import load_yaml_dataset


class TaskRequester(RopodPyre):
    def __init__(self, robot_id):
        zyre_config = {'node_name': 'task_request_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['TASK', 'ALLOCATION']}
        super().__init__(zyre_config, acknowledge=False)

        ccu_store = CCUStore('ropod_ccu_store')
        self.ccu_store_interface = DBInterface(ccu_store)

        robot_store = CCUStore('ropod_store_' + robot_id)
        self.robot_store_interface = DBInterface(robot_store)

        self.allocations = list()
        self.n_tasks = 0
        self.terminated = False

    def tear_down(self):
        self.logger.info("Resetting the ccu_store")
        self.ccu_store_interface.clean()
        self.logger.info("Resetting the robot_store")
        self.robot_store_interface.clean()

    def allocate(self, tasks):
        self.n_tasks = len(tasks)
        for task in tasks:
            self.request_allocation(task)

    def request_allocation(self, task):
        logging.debug("Requesting allocation of task %s", task.task_id)
        task_msg = dict()
        task_msg['header'] = dict()
        task_msg['payload'] = dict()
        task_msg['header']['type'] = 'ALLOCATE-TASK'
        task_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        task_msg['header']['msgId'] = generate_uuid()
        task_msg['header']['timestamp'] = TimeStamp().to_str()

        task_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'
        task_msg['payload']['task'] = task.to_dict()

        self.shout(task_msg)

    def receive_msg_cb(self, msg_content):
        msg = self.convert_zyre_msg_to_dict(msg_content)
        if msg is None:
            return

        if msg['header']['type'] == 'ALLOCATION':
            self.logger.debug("Received allocation message")
            task_id = msg['payload']['task_id']
            winner_id = msg['payload']['robot_id']
            allocation = (task_id, [winner_id])
            self.allocations.append(allocation)
            logging.debug("Receiving allocation %s", allocation)
            self.check_termination_test()

    def check_termination_test(self):
        if len(self.allocations) == self.n_tasks:
            logging.debug("Terminating test")
            self.terminated = True


if __name__ == '__main__':
    tasks = load_yaml_dataset('data/non_overlapping.yaml')
    robot_id = 'ropod_001'

    timeout_duration = 300  # 5 minutes

    test = TaskRequester(robot_id)
    test.start()

    try:
        test.tear_down()
        time.sleep(5)
        test.allocate(tasks)
        start_time = time.time()
        while not test.terminated and start_time + timeout_duration > time.time():
            time.sleep(0.5)
        test.tear_down()
    except (KeyboardInterrupt, SystemExit):
        print('Task request test interrupted; exiting')

    print("Exiting test...")
    test.shutdown()



