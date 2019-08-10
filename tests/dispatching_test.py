import logging
import yaml
import json

from fleet_management.config.loader import Config
from mrs.utils.datasets import load_yaml_dataset
from mrs.timetable import Timetable


class TestDispatcher(object):
    def __init__(self, robot_id, timetable_file, tasks, config_file=None):
        self.logger = logging.getLogger('test')

        config = Config(config_file, initialize=True)
        config.configure_logger()
        self.ccu_store = config.configure_ccu_store()
        self.robot_id = robot_id

        self.robot = config.configure_robot_proxy(robot_id, self.ccu_store)

        timetable = self.read_timetable(timetable_file)
        self.ccu_store.add_timetable(timetable)
        self.load_tasks(tasks)
        self.robot.run()

    def load_tasks(self, tasks):
        for task in tasks:
            self.ccu_store.add_task(task)

    def read_timetable(self, timetable_file):
        with open(timetable_file, 'r') as file:
            timetable_dict = yaml.safe_load(file)

        robot_id = timetable_dict['robot_id']
        stn_dict = timetable_dict['stn']
        dispatchable_graph_dict = timetable_dict['dispatchable_graph']
        schedule_dict = timetable_dict['schedule']

        stn_json = json.dumps(stn_dict)
        dispatchable_graph_json = json.dumps(dispatchable_graph_dict)
        schedule_json = json.dumps(schedule_dict)

        timetable_dict2 = dict()
        timetable_dict2['robot_id'] = robot_id
        timetable_dict2['stn'] = stn_json
        timetable_dict2['dispatchable_graph'] = dispatchable_graph_json
        timetable_dict2['schedule'] = schedule_json

        timetable = Timetable.from_dict(timetable_dict2, self.robot.dispatcher.stp)
        return timetable


if __name__ == '__main__':
    config_file = '../config/config.yaml'
    timetable_file = 'data/timetable.yaml'
    tasks = load_yaml_dataset('data/allocated_tasks.yaml')

    test = TestDispatcher('ropod_001', timetable_file, tasks, config_file)
