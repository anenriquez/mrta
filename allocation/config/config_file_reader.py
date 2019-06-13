import yaml
import logging
from allocation.config.params import ConfigParams, RopodParams


class ConfigFileReader(object):
    ''' Adapted from fleet_management.config.config_file_reader
        @author Alex Mitrevski
        @contact aleksandar.mitrevski@h-brs.de
        An interface for reading task allocation configuration files
'''
    @staticmethod
    def load(config_file):
        '''Loads task allocation configuration parameters from the given YAML file

        Keyword arguments:
        @param config_file absolute path of a config file

        '''
        logger = logging.getLogger('allocation.config.reader')
        config_params = ConfigParams()
        config_data = ConfigFileReader.__read_yaml_file(config_file)

        if 'ropods' in config_data.keys():
            for ropod_id, params in config_data['ropods'].items():
                ropod_params = RopodParams()
                ropod_params.id = ropod_id
                config_params.ropods.append(ropod_params)
        else:
            logger.error('Config error: "ropods" not specified')
            return ConfigParams()

        if 'bidding_rule' in config_data.keys():
            config_params.bidding_rule = config_data['bidding_rule']
        else:
            logger.error('Config error: "bidding_rule" not specified')
            return ConfigParams()

        if 'auction_time' in config_data.keys():
            config_params.auction_time = config_data['auction_time']
        else:
            logger.error('Config error: "auction_time" not specified')
            return ConfigParams()

        if 'scheduling_method' in config_data.keys():
            config_params.scheduling_method = config_data['scheduling_method']
        else:
            logger.error('Config error: "scheduling_method" not specified')
            return ConfigParams()

        if 'zyre_group_name' in config_data.keys():
            config_params.zyre_group_name = config_data['zyre_group_name']
        else:
            logger.error('Config error: "zyre_group_name" not specified')
            return ConfigParams()

        if 'task_allocator_zyre_params' in config_data.keys():
            config_params.task_allocator_zyre_params.groups = config_data['task_allocator_zyre_params']['groups']
            config_params.task_allocator_zyre_params.message_types = config_data['task_allocator_zyre_params']['message_types']
        else:
            logger.error('Config error: "task_allocator_zyre_params" not specified')

        return config_params

    @staticmethod
    def __read_yaml_file(config_file_name):
        file_handle = open(config_file_name, 'r')
        data = yaml.load(file_handle)
        file_handle.close()
        return data
