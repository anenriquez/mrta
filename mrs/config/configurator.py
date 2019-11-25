from fmlib.api import API
from fmlib.config.builders import Store
from fmlib.config.params import ConfigParams
from mrs.config.mrta import MRTAFactory
import logging.config
from mrs.timetable.timetable import Timetable

ConfigParams.default_config_module = 'mrs.config.default'


class Configurator:
    def __init__(self, config_file=None):

        if config_file is None:
            self.config_params = ConfigParams.default()
        else:
            self.config_params = ConfigParams.from_file(config_file)

        self.logger = logging.getLogger('mrs')
        logger_config = self.config_params.get('logger')
        logging.config.dictConfig(logger_config)

        self.builder = MRTAFactory(self.config_params.get('allocation_method'))

    def config_ccu(self):
        api_config = self.config_params.get('ccu_api')
        api = API(**api_config)
        store_config = self.config_params.get('ccu_store')
        store = Store(**store_config)

        self.builder.register_component('api', api)
        self.builder.register_component('ccu_store', store)

        components = self.builder(**self.config_params.get('ccu'))

        fleet = self.config_params.get('fleet')
        for component_name, component in components.items():
            if hasattr(component, 'register_robot'):
                for robot_id in fleet:
                    component.register_robot(robot_id)

        return components

    def config_robot(self, robot_id):
        api_config = self.config_params.get('robot_api')
        api_config['zyre']['zyre_node']['node_name'] = robot_id
        api = API(**api_config)
        store_config = self.config_params.get('robot_store')
        store_config['db_name'] = store_config['db_name'] + '_' + robot_id.split('_')[1]
        store = Store(**store_config)

        self.builder.register_component('api', api)
        self.builder.register_component('robot_store', store)
        self.builder.register_component('timetable', Timetable(robot_id, self.builder.get_stp_solver()))
        self.builder.register_component('robot_id', robot_id)

        robot_config = self.config_params.get('robot')
        robot_config.update(robot_id=robot_id)

        components = self.builder(**robot_config)

        return components





