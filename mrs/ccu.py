import logging
import time

from fleet_management.config.loader import Configurator


class FMS(object):
    def __init__(self, config_file=None):
        self.logger = logging.getLogger('mrs')
        self.logger.info("------>Configuring MRS ...")

        config = Configurator(config_file)
        self.api = config.api
        ccu_store = config.ccu_store

        self.resource_manager = config.resource_manager

        config._configure_plugins(ccu_store=ccu_store,
                                       api=self.api)

        config.add_plugins('resource_manager')

        self.api.register_callbacks(self)

        self.logger.info("Initialized FMS")

    def run(self):
        try:
            self.api.start()

            while True:
                self.resource_manager.auctioneer.run()
                self.resource_manager.get_allocation()
                self.api.run()
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.api.shutdown()
            self.logger.info('FMS is shutting down')

    def shutdown(self):
        self.api.shutdown()


if __name__ == '__main__':
    config_file = '../config/config.yaml'
    fms = FMS(config_file)

    fms.run()
