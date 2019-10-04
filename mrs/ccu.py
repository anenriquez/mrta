import logging
import time

from fmlib.api import API
from fmlib.config.builders import Store
from fmlib.models.tasks import Task
from ropod.structs.task import TaskStatus as TaskStatusConst

from mrs.config.mrta import MRTAFactory
from mrs.utils.datasets import load_yaml


class MRS(object):
    def __init__(self, config_file=None):

        self.logger = logging.getLogger('mrs')
        config_params = load_yaml(config_file)

        logger_config = config_params.get('logger')
        logging.config.dictConfig(logger_config)

        api_config = config_params.get('api')
        store_config = config_params.get('ccu_store')
        self.api = API(**api_config)
        self.ccu_store = Store(**store_config)

        config = config_params.get('plugins').get('mrta')
        allocation_method = config_params.get('allocation_method')
        mrta_factory = MRTAFactory(allocation_method)
        components = mrta_factory(**config)

        for component_name, component in components.items():
            if hasattr(component, 'configure'):
                self.logger.debug("Configuring %s", component_name)
                component.configure(api=self.api, ccu_store=self.ccu_store)

        self.auctioneer = components.get('auctioneer')
        self.dispatcher = components.get('dispatcher')

        self.api.register_callbacks(self)
        self.logger.info("Initialized MRS")

    def start_test_cb(self, msg):
        self.logger.debug("Start test msg received")
        tasks = Task.get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        self.auctioneer.allocate(tasks)

    def run(self):
        try:
            self.api.start()

            while True:
                self.auctioneer.run()
                self.api.run()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.api.shutdown()
            self.logger.info('FMS is shutting down')

    def shutdown(self):
        self.api.shutdown()


if __name__ == '__main__':
    config_file_path = 'config/default/config.yaml'
    fms = MRS(config_file_path)

    fms.run()
