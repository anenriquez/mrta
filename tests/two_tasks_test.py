from allocation.task_allocator import TaskAllocator
# from allocation.config.config_file_reader import ConfigFileReader
from allocation.config.loader import Config
import yaml
import uuid
import time
from allocation.api.zyre import ZyreAPI


if __name__ == '__main__':
    dataset_id = "TDU-TGR-1.yaml"
    config = Config("../config/config-v2.yaml")
    # config_params = config.get_config_params()

    zyre_api = config.configure_api('task_allocator')
    # api_config = config_params.get('api')
    # zyre_config = api_config.get('zyre')
    # zyre_api = ZyreAPI(zyre_config)

    # config_params = ConfigFileReader.load("../config/config.yaml")

    task_allocator = TaskAllocator(zyre_api)
    task_allocator.api.start()
    task_allocator.allocate_dataset(dataset_id)

    try:
        while not task_allocator.api.terminated:
            time.sleep(0.8)
    except (KeyboardInterrupt, SystemExit):
        print('Experiment initiator interrupted; exiting')

    print("Exiting task allocator...")
    task_allocator.api.shutdown()
