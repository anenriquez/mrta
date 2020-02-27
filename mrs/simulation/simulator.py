import threading
from datetime import datetime

import dateutil.parser
import simpy.rt
from ropod.utils.timestamp import TimeStamp


class Simulator:
    def __init__(self, initial_time, factor=0.05, **kwargs):
        """ Controls the simulation time

        initial_time(datetime): Datetime object representing initial time
        factor(float): Time (in seconds) between each simulation step,
                        e.g. with a factor of 0.05, a step is incremented every 0.05 seconds
        """
        self._factor = factor
        self._env = simpy.Environment(initial_time=initial_time.timestamp())
        self._timer = None
        self.current_time = initial_time

    def set_initial_time(self, initial_time):
        initial_time = dateutil.parser.parse(initial_time).timestamp()
        self._env = simpy.Environment(initial_time=initial_time)
        self.current_time = initial_time

    def step(self):
        self.current_time = datetime.fromtimestamp(self._env.now)
        yield self._env.timeout(1)

    def run(self):
        self._timer = threading.Timer(self._factor, self.run)
        self._timer.start()
        self._env.process(self.step())
        self._env.run()

    def stop(self):
        if self._timer:
            self._timer.cancel()

    def is_valid_time(self, time_):
        """ Returns:
            - True if the given time_ is in the future,
            - False otherwise
        """
        if time_ > self.current_time:
            return True
        return False


class SimulatorInterface:
    def __init__(self, simulator):
        self.simulator = simulator
        self._started = False

    def start(self, initial_time):
        self._started = True
        if self.simulator:
            self.simulator.set_initial_time(initial_time)
            self.run()

    def stop(self):
        self._started = False
        if self.simulator:
            self.simulator.stop()

    def is_valid_time(self, time_):
        if self.simulator:
            return self.simulator.is_valid_time(time_)
        else:
            if time_ > datetime.now():
                return True
            return False

    def get_current_time(self):
        if self.simulator:
            return self.simulator.current_time
        else:
            return datetime.now()

    def get_current_timestamp(self):
        if self.simulator:
            return TimeStamp.from_datetime(self.simulator.current_time)
        else:
            return TimeStamp()

    def init_ztp(self):
        midnight = self.get_current_time().replace(hour=0, minute=0, second=0, microsecond=0)
        ztp = TimeStamp()
        ztp.timestamp = midnight
        return ztp

    def run(self):
        if self.simulator and self._started:
            self.simulator.run()
