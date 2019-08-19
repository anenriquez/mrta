import logging
import time
import uuid

from fleet_management.config.loader import Config
from fleet_management.db.ccu_store import CCUStore
from ropod.pyre_communicator.base_class import RopodPyre
from stn.stp import STP

from mrs.db_interface import DBInterface
from mrs.structs.timetable import Timetable
from mrs.utils.datasets import load_yaml_dataset


class TaskRequester(RopodPyre):
    def __init__(self, config_file):
        zyre_config = {'node_name': 'task_request_test',
                       'groups': ['TASK-ALLOCATION'],
                       'message_types': ['TASK', 'ALLOCATION']}
        super().__init__(zyre_config, acknowledge=False)

        config = Config(config_file, initialize=False)
        ccu_store = CCUStore('ropod_ccu_store')
        self.db_interface = DBInterface(ccu_store)

        allocator_config = config.config_params.get("plugins").get("task_allocation")
        stp_solver = allocator_config.get('bidding_rule').get('robustness')
        self.stp = STP(stp_solver)
        self.robot_ids = config.config_params.get('resources').get('fleet')

        self.auctioneer_name = allocator_config.get('auctioneer')
        self.allocations = list()
        self.n_tasks = 0
        self.terminated = False

    def reset_timetables(self):
        logging.info("Resetting timetables")
        for robot_id in self.robot_ids:
            timetable = Timetable(self.stp, robot_id)
            self.db_interface.update_timetable(timetable)

    def reset_tasks(self):
        logging.info("Resetting tasks")
        tasks_dict = self.db_interface.get_tasks()
        for task_id, task_info in tasks_dict.items():
            self.db_interface.remove_task(task_id)

    def allocate(self, tasks):
        self.n_tasks = len(tasks)
        for task in tasks:
            self.request_allocation(task)

    def request_allocation(self, task):
        logging.debug("Requesting allocation of task %s", task.id)
        task_msg = dict()
        task_msg['header'] = dict()
        task_msg['payload'] = dict()
        task_msg['header']['type'] = 'TASK'
        task_msg['header']['metamodel'] = 'ropod-msg-schema.json'
        task_msg['header']['msgId'] = str(uuid.uuid4())
        task_msg['header']['timestamp'] = int(round(time.time()) * 1000)

        task_msg['payload']['metamodel'] = 'ropod-bid_round-schema.json'
        task_msg['payload']['task'] = task.to_dict()

        self.whisper(task_msg, peer=self.auctioneer_name)

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
    tasks = load_yaml_dataset('data/non_overlapping_1.yaml')
    config_file_path = '../config/config.yaml'

    for task in tasks:
        print(task.id)

    timeout_duration = 300  # 5 minutes

    test = TaskRequester(config_file_path)
    test.start()

    try:
        time.sleep(5)
        test.reset_timetables()
        test.reset_tasks()
        test.allocate(tasks)
        start_time = time.time()
        while not test.terminated and start_time + timeout_duration > time.time():
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        print('Task request test interrupted; exiting')

    print("Exiting test...")
    test.shutdown()



