import time


class Robot(object):
    def __init__(self, robot_id, bidder, **kwargs):
        self.logger = logging.getLogger('mrs.robot.%s' % robot_id)

        self.robot_id = robot_id
        self.api = kwargs.get('api')
        self.robot_store = kwargs.get('robot_store')
        self.bidder = bidder
        self.executor_interface = kwargs.get('executor_interface')

        if self.api:
            self.api.register_callbacks(self)

        self.logger.info("Initialized Robot %s", robot_id)

    def configure(self, **kwargs):
        api = kwargs.get('api')
        robot_store = kwargs.get('robot_store')
        if api:
            self.api = api
            self.api.register_callbacks(self)
        if robot_store:
            self.robot_store = robot_store

    def run(self):
        try:
            self.api.start()
            while True:
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Terminating %s robot ...", self.robot_id)
            self.api.shutdown()
            self.logger.info("Exiting...")


if __name__ == '__main__':

    import argparse
    import logging.config
    from mrs.config.mrta import MRTAFactory
    from fmlib.config.params import ConfigParams

    ConfigParams.default_config_module = 'mrs.config.default'

    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, action='store', help='Path to the config file')

    parser.add_argument('robot_id', type=str, help='example: ropod_001')

    args = parser.parse_args()

    if args.file is None:
        config_params = ConfigParams.default()
    else:
        config_params = ConfigParams.from_file(args.file)

    logger_config = config_params.get('logger')
    logging.config.dictConfig(logger_config)

    config = config_params.get('robot_proxy')
    allocation_method = config_params.get('allocation_method')
    config.update({'robot_id': args.robot_id})
    robot_config = {'robot': config}

    mrta_factory = MRTAFactory(allocation_method)
    components = mrta_factory(**robot_config)

    robot_components = components.get('robot')
    robot = Robot(args.robot_id, **robot_components)
    robot.run()

