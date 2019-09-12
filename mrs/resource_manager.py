import logging

from fleet_management.db.queries.interfaces.tasks import get_tasks_by_status
from fleet_management.resource_manager import ResourceManager as RopodResourceManager
from ropod.structs.task import TaskStatus as TaskStatusConst


class ResourceManager(RopodResourceManager):

    def __init__(self, ccu_store, api, **kwargs):
        super().__init__(ccu_store, api, **kwargs)
        self.logger = logging.getLogger('mrs.resources.manager')

    def start_test_cb(self, msg):
        self.logger.debug("Start test msg received")
        tasks = get_tasks_by_status(TaskStatusConst.UNALLOCATED)
        self.allocate(tasks)

    # TODO: Once an allocation is completed, assign robots to the Task
    #  (in ropod this is done by the TaskManager)

