import yaml
from allocation.api.zyre import ZyreAPI


class Config(object):
    def __init__(self, config_file, initialize=True):
        config = Config.load_file(config_file)
        self.config_params = dict()
        self.config_params.update(**config)
        # if initialize:
        #     self.api = self.configure_api()

    def configure_api(self, node_name):
        api_config = self.config_params.get('api')
        zyre_config = api_config.get('zyre')
        zyre_config.update({'node_name': node_name})
        zyre_api = ZyreAPI(zyre_config)
        return zyre_api

    def get_config_params(self):
        return self.config_params

    @staticmethod
    def load_file(config_file):
        file_handle = open(config_file, 'r')
        data = yaml.safe_load(file_handle)
        file_handle.close()
        return data

    # def read_yaml_file(config_file_name):
    #     file_handle = open(config_file_name, 'r')
    #     data = yaml.safe_load(file_handle)
    #     file_handle.close()
    #     return data
