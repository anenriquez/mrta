import logging
from fmlib.api import API
from fmlib.config.builders import Store

from mrs.bidding.bidder import Bidder
from mrs.scheduling.monitor import ScheduleMonitor
from mrs.timetable.timetable import Timetable
from datetime import datetime
from ropod.utils.timestamp import TimeStamp


class RobotFactory:
    def __init__(self):
        self.logger = logging.getLogger('mrta.config.components.robot')

        self._api = None
        self._robot_store = None
        self._timetable = None
        self._components = dict()

        self.register_component('bidder', Bidder)
        self.register_component('schedule_monitor', ScheduleMonitor)

    def register_component(self, component_name, component):
        self._components[component_name] = component

    @staticmethod
    def get_robot_api(robot_id, api_config):
        api_config['zyre']['zyre_node']['node_name'] = robot_id
        api = API(**api_config)
        return api

    @staticmethod
    def get_robot_store(robot_id, robot_store_config):
        robot_store_config['db_name'] = robot_store_config['db_name'] + '_' + robot_id.split('_')[1]
        robot_store = Store(**robot_store_config)
        return robot_store

    @staticmethod
    def get_robot_timetable(robot_id, stp_solver):
        timetable = Timetable(robot_id, stp_solver)
        timetable.fetch()
        today_midnight = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        timetable.zero_timepoint = TimeStamp()
        timetable.zero_timepoint.timestamp = today_midnight
        return timetable

    def __call__(self, allocation_method, stp_solver, timetable_manager, **robot_config):
        components = dict()

        robot_id = robot_config.pop('robot_id')
        api_config = robot_config.pop('api')
        robot_store_config = robot_config.pop('robot_store')

        if not self._api:
            self._api = self.get_robot_api(robot_id, api_config)
        if not self._robot_store:
            self._robot_store = self.get_robot_store(robot_id, robot_store_config)
        if not self._timetable:
            self._timetable = self.get_robot_timetable(robot_id, stp_solver)

        components['api'] = self._api
        components['robot_store'] = self._robot_store

        for component_name, configuration in robot_config.items():
            self.logger.debug("Creating %s", component_name)
            component = self._components.get(component_name)
            if component:
                _instance = component(allocation_method=allocation_method,
                                      robot_id=robot_id,
                                      stp_solver=stp_solver,
                                      api=self._api,
                                      robot_store=self._robot_store,
                                      timetable=self._timetable,
                                      **configuration)

                components[component_name] = _instance

        return components

