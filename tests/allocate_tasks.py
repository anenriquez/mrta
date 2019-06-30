from allocation.config.loader import Config
from allocation.allocation_requester import AllocationRequester
import logging
from datasets.dataset_loader import load_dataset
import time


if __name__ == '__main__':

    logger = logging.getLogger('test')
    logger.info("Running task allocation test...")

    config = Config("../config/config.yaml")

    allocation_requester_config = config.configure_allocation_requester()
    allocation_requester = AllocationRequester(**allocation_requester_config)

    tasks = load_dataset('three_tasks.csv')

    for task in tasks:
        print(task.id)

    allocation_requester.request_allocation(tasks)

    try:
        while not allocation_requester.api.terminated:
            time.sleep(0.8)
    except (KeyboardInterrupt, SystemExit):
        print('Experiment initiator interrupted; exiting')

    print("Exiting task allocator...")
    allocation_requester.api.shutdown()
