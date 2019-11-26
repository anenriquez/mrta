import argparse
import logging.config
import time

from fmlib.api import API
from fmlib.config.builders import Store
from fmlib.config.params import ConfigParams
from fmlib.models.tasks import Task
from mrs.config.mrta import MRTAFactory
from ropod.structs.task import TaskStatus as TaskStatusConst
from mrs.execution.archive_task import ArchiveTask

ConfigParams.default_config_module = 'mrs.config.default'


class MRS(object):
    def __init__(self, config_file=None):

        self.logger = logging.getLogger('mrs')

        if config_file is None:
            self.config_params = ConfigParams.default()
        else:
            self.config_params = ConfigParams.from_file(config_file)

        logger_config = self.config_params.get('logger')
        logging.config.dictConfig(logger_config)

        self.api = self.get_api()
        self.ccu_store = self.get_ccu_store()

        components = self.get_mrta_components()
        self.auctioneer = components.get('auctioneer')
        self.dispatcher = components.get('dispatcher')

        self.api.register_callbacks(self)
        self.logger.info("Initialized MRS")

    def get_api(self):
        api_config = self.config_params.get('api')
        return API(**api_config)

    def get_ccu_store(self):
        store_config = self.config_params.get('ccu_store')
        return Store(**store_config)

    def get_mrta_components(self):
        allocation_method = self.config_params.get('allocation_method')
        fleet = self.config_params.get('resource_manager').get('resources').get('fleet')
        mrta_factory = MRTAFactory(allocation_method)

        config = self.config_params.get('plugins').get('mrta')
        components = mrta_factory(**config)

        for component_name, component in components.items():
            if hasattr(component, 'configure'):
                self.logger.debug("Configuring %s", component_name)
                component.configure(api=self.api, ccu_store=self.ccu_store)
            if hasattr(component, 'register_robot'):
                for robot_id in fleet:
                    component.register_robot(robot_id)

        return components

    def start_test_cb(self, msg):
        self.logger.debug("Start test msg received")
        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        self.auctioneer.allocate(tasks)

    def archive_task_cb(self, msg):
        payload = msg['payload']
        archive_task = ArchiveTask.from_payload(payload)
        self.auctioneer.archive_task(archive_task.robot_id, archive_task.task_id, archive_task.node_id)
        self.dispatcher.timetable_manager.send_update_to = archive_task.robot_id

    def run(self):
        try:
            self.api.start()

            while True:
                self.auctioneer.run()
                self.dispatcher.run()
                self.api.run()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.api.shutdown()
            self.logger.info('FMS is shutting down')

    def shutdown(self):
        self.api.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')

    args = parser.parse_args()
    mrs = MRS(args.file)
    mrs.run()
