from fmlib.api import API
from fmlib.config.builders import Store
from fleet_management.config.builder import FMSBuilder
from mrs.config.mrta import MRTAFactory


_component_modules = {'api': API,
                      'robot_store': Store,
                      }

_config_order = ['api', 'robot_store']


def get_robot_config(robot_id, config_params):
    robot_config = config_params.get('robot_proxy')

    api_config = robot_config.get('api')
    api_config['zyre']['zyre_node']['node_name'] = robot_id
    robot_config.update({'api': api_config})

    db_config = robot_config.get('robot_store')
    db_config['db_name'] = db_config['db_name'] + '_' + robot_id.split('_')[1]
    robot_config.update({'robot_store': db_config})

    for component_name, config in robot_config.items():
        config.update({'robot_id': robot_id})

    return robot_config


class RobotBuilder:

    def __call__(self, robot_id, config_params):

        robot_config = get_robot_config(robot_id, config_params)

        fms_builder = FMSBuilder(component_modules=_component_modules,
                                 config_order=_config_order)
        fms_builder.configure(robot_config)

        api = fms_builder.get_component('api')
        robot_store = fms_builder.get_component('robot_store')

        robot_config.pop('api')
        robot_config.pop('robot_store')

        allocation_method = config_params.get('allocation_method')
        mrta_factory = MRTAFactory(allocation_method)

        components = mrta_factory(**robot_config)
        components.update({'api': api})

        for component_name, component in components.items():
            if hasattr(component, 'configure'):
                component.configure(api=api, robot_store=robot_store)

        return components


configure = RobotBuilder()


