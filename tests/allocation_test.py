import logging
import time
import uuid

from fleet_management.config.loader import Configurator
from fleet_management.db.ccu_store import CCUStore
from ropod.pyre_communicator.base_class import RopodPyre
from stn.stp import STP

from ropod.utils.timestamp import TimeStamp
from ropod.utils.uuid import generate_uuid

from mrs.db_interface import DBInterface
from mrs.structs.timetable import Timetable
from mrs.utils.datasets import load_yaml_dataset


class TaskRequester(RopodPyre):
    def __init__(self, config_file):
        zyre_config = {'node_name': 'task_request_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['TASK', 'ALLOCATION']}
        super().__init__(zyre_config, acknowledge=False)

        config = Configurator(config_file, initialize=False)
        ccu_store = CCUStore('ropod_ccu_store')
        self.db_interface = DBInterface(ccu_store)

        allocator_config = config._config_params.get("plugins").get("task_allocation")
        robot_proxy = config._config_params.get("robot_proxy")
        stp_solver = allocator_config.get('stp_solver')
        self.stp = STP(stp_solver)
        self.robot_ids = config._config_params.get('resource_manager').get('resources').get('fleet')

        self.auctioneer_name = robot_proxy.get("bidder").get("auctioneer_name")
        self.allocations = list()
        self.n_tasks = 0
        self.terminated = False

    def reset_timetables(self):
        logging.info("Resetting timetables")
        for robot_id in self.robot_ids:
            timetable = Timetable(robot_id, self.stp)
            self.db_interface.update_timetable(timetable)
            self.send_timetable(timetable, robot_id)

    def reset_tasks(self):
        logging.info("Resetting tasks")
        tasks_dict = self.db_interface.get_tasks()
        for task_id, task_dict in tasks_dict.items():
            self.db_interface.remove_task(task_id)
            self.request_task_delete(task_dict)

    def send_timetable(self, timetable, robot_id):
        logging.debug("Sending timetable to %s", robot_id)
        timetable_msg = dict()
        timetable_msg['header'] = dict()
        timetable_msg['payload'] = dict()
        timetable_msg['header']['type'] = 'TIMETABLE'
        timetable_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        timetable_msg['header']['msgId'] = generate_uuid()
        timetable_msg['header']['timestamp'] = TimeStamp().to_str()

        timetable_msg['payload']['metamodel'] = 'ropod-bid_round-sch(self.round_time)ema.json'
        timetable_msg['payload']['timetable'] = timetable.to_dict()
        self.shout(timetable_msg)

    def allocate(self, tasks):
        self.n_tasks = len(tasks)
        for task in tasks:
            self.request_allocation(task)

    def request_allocation(self, task):
        logging.debug("Requesting allocation of task %s", task.id)
        task_msg = dict()
        task_msg['header'] = dict()
        task_msg['payload'] = dict()
        task_msg['header']['type'] = 'ALLOCATE-TASK'
        task_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        task_msg['header']['msgId'] = generate_uuid()
        task_msg['header']['timestamp'] = TimeStamp().to_str()

        task_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'
        task_msg['payload']['task'] = task.to_dict()

        self.whisper(task_msg, peer=self.auctioneer_name)

    def request_task_delete(self, task_dict):
        logging.debug("Requesting delete of task %s", task_dict['id'])
        task_msg = dict()
        task_msg['header'] = dict()
        task_msg['payload'] = dict()
        task_msg['header']['type'] = 'DELETE-TASK'
        task_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        task_msg['header']['msgId'] = generate_uuid()
        task_msg['header']['timestamp'] = TimeStamp().to_str()

        task_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'
        task_msg['payload']['task'] = task_dict

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
    tasks = load_yaml_dataset('data/non_overlapping_3.yaml')
    config_file_path = '../config/config.yaml'

    for task in tasks:
        print(task.to_dict())

    timeout_duration = 300  # 5 minutes

    test = TaskRequester(config_file_path)
    test.start()

    try:
        time.sleep(5)
        test.reset_timetables()
        test.reset_tasks()
        time.sleep(5)
        test.allocate(tasks)
        start_time = time.time()
        while not test.terminated and start_time + timeout_duration > time.time():
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        print('Task request test interrupted; exiting')

    print("Exiting test...")
    test.shutdown()



