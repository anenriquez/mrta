from allocation.task_allocator import TaskAllocator
from allocation.config.config_file_reader import ConfigFileReader
import yaml
import uuid
import time

if __name__ == '__main__':
    dataset_id = "TDU-TGR-1.yaml"
    config_params = ConfigFileReader.load("../config/config.yaml")

    task_allocator = TaskAllocator(config_params)
    task_allocator.start()
    task_allocator.allocate_dataset(dataset_id)

    try:
        while not task_allocator.terminated:
            time.sleep(0.8)
    except (KeyboardInterrupt, SystemExit):
        print('Experiment initiator interrupted; exiting')

    print("Exiting task allocator...")
    task_allocator.shutdown()
