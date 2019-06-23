from allocation.config.loader import Config
from allocation.task_sender import TaskSender
import logging

import time


if __name__ == '__main__':

    logger = logging.getLogger('test')
    logger.info("Running test...")

    dataset_id = "TDU-TGR-1.yaml"
    config = Config("../config/config-v2.yaml")

    task_sender_config = config.configure_task_sender()
    task_sender = TaskSender(**task_sender_config)
    # auctioneer = config.configure_auctioneer()
    #
    # auctioneer.api.start()

    # task_sender.api.start()
    task_sender.allocate_dataset(dataset_id)

    # try:
    #     while not auctioneer.api.terminated and not task_sender.api.terminated:
    #         auctioneer.announce_task()
    #         time.sleep(0.5)
    # except (KeyboardInterrupt, SystemExit):
    #     logging.info("Auctioneer terminated; exiting")
    #
    # logging.info("Exiting auctioneer")
    # auctioneer.api.shutdown()
    # logging.info("Exiting task allocator...")
    # task_sender.api.shutdown()


    try:
        while not task_sender.api.terminated:
            time.sleep(0.8)
    except (KeyboardInterrupt, SystemExit):
        print('Experiment initiator interrupted; exiting')

    print("Exiting task allocator...")
    task_sender.api.shutdown()
