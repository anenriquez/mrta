import logging.config

from fmlib.api import API
from fmlib.config.builders import Store
from mrs.config.builder import MRTABuilder


class Configurator:
    def __init__(self, config_params, **kwargs):

        self._config_params = config_params

        self.logger = logging.getLogger('mrs')
        logger_config = self._config_params.get('logger')
        logging.config.dictConfig(logger_config)

        allocation_method = self._config_params.get('allocation_method')
        self._factory = MRTABuilder(allocation_method, **kwargs)
        self._components = dict()

    def configure(self, **config):
        components = self._factory(**config)
        self._components.update(**components)
        self.register_fleet()

    def register_fleet(self):
        fleet = self._config_params.get('fleet')
        for component_name, component in self._components.items():
            if hasattr(component, 'register_robot'):
                for robot_id in fleet:
                    component.register_robot(robot_id)

    def register_robot_id(self, robot_id):
        self._factory.register_component('robot_id', robot_id)

    def register_api(self, component_name, **kwargs):
        robot_id = kwargs.get("robot_id")
        api_config = self._config_params.get(component_name + '_api')

        if robot_id and component_name == 'robot_proxy':
            api_config['zyre']['zyre_node']['node_name'] = robot_id + '_proxy'
        elif robot_id and component_name == 'robot':
            api_config['zyre']['zyre_node']['node_name'] = robot_id

        self._factory.register_component('api', API(**api_config))

    def register_store(self, component_name, **kwargs):
        robot_id = kwargs.get("robot_id")
        store_config = self._config_params.get(component_name + '_store')
        if robot_id:
            store_config['db_name'] = store_config['db_name'] + '_' + robot_id.split('_')[1]
        self._factory.register_component(component_name + '_store', Store(**store_config))

    def config_ccu(self):
        self.register_api('ccu')
        self.register_store('ccu')
        self.configure(**self._config_params)
        return self._components

    def config_robot_proxy(self, robot_id):
        self.register_api('robot_proxy', robot_id=robot_id)
        self.register_store('robot_proxy', robot_id=robot_id)
        self.register_robot_id(robot_id)
        self.configure(**self._config_params)
        return self._components

    def config_robot(self, robot_id):
        self.register_api('robot', robot_id=robot_id)
        self.register_store('robot', robot_id=robot_id)
        self.register_robot_id(robot_id)
        self.configure(**self._config_params)
        return self._components
