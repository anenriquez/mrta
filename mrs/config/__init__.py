from mrs.config.builder import MRTABuilder
from mrs.task_allocation import auctioneer
from mrs.task_execution import dispatcher

configure = MRTABuilder(auctioneer.configure, dispatcher.configure)
