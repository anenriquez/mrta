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
        self._components = dict()

        self.register_component('bidder', Bidder)
        self.register_component('schedule_monitor', ScheduleMonitor)

    def register_component(self, component_name, component):
        self._components[component_name] = component

    def api(self, robot_id, api_config):
        self.logger.debug("Creating api of %s", robot_id)
        api_config['zyre']['zyre_node']['node_name'] = robot_id
        api = API(**api_config)
        return api

    def robot_store(self, robot_id, robot_store_config):
        self.logger.debug("Creating robot_store %s", robot_id)
        robot_store_config['db_name'] = robot_store_config['db_name'] + '_' + robot_id.split('_')[1]
        robot_store = Store(**robot_store_config)
        return robot_store

    def timetable(self, robot_id, stp_solver):
        self.logger.debug("Creating timetable %s", robot_id)
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

        api = self.api(robot_id, api_config)
        robot_store = self.robot_store(robot_id, robot_store_config)
        timetable = self.timetable(robot_id, stp_solver)

        components['api'] = api
        components['robot_store'] = robot_store

        for component_name, configuration in robot_config.items():
            self.logger.debug("Creating %s", component_name)
            component = self._components.get(component_name)
            if component:
                _instance = component(allocation_method=allocation_method,
                                      robot_id=robot_id,
                                      stp_solver=stp_solver,
                                      api=api,
                                      robot_store=robot_store,
                                      timetable=timetable,
                                      **configuration)

                components[component_name] = _instance

        return components

