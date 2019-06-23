from allocation.config.loader import Config
from allocation.task_requester import TaskRequester
import logging

import time


if __name__ == '__main__':

    logger = logging.getLogger('test')
    logger.info("Running test...")

    dataset_id = "TDU-TGR-1.yaml"
    config = Config("../config/config.yaml")

    task_sender_config = config.configure_task_sender()
    task_sender = TaskRequester(**task_sender_config)

    task_sender.allocate_dataset(dataset_id)

    try:
        while not task_sender.api.terminated:
            time.sleep(0.8)
    except (KeyboardInterrupt, SystemExit):
        print('Experiment initiator interrupted; exiting')

    print("Exiting task allocator...")
    task_sender.api.shutdown()
