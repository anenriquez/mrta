from datetime import datetime

import simpy.rt
from ropod.utils.timestamp import TimeStamp


class Simulator:
    def __init__(self, initial_time, factor=0.05, **kwargs):
        """ Controls the simulation time

        initial_time(datetime): Datetime object representing initial time
        factor(float): Real time (in seconds) that passes between each simulation step
                        e.g. with a factor of 0.05, a simulation step takes 0.05 seconds
        """
        self.env = simpy.rt.RealtimeEnvironment(initial_time=initial_time.timestamp(), factor=factor, strict=False)
        self.current_time = initial_time

    def get_current_time(self):
        return self.current_time

    def step(self):
        self.current_time = datetime.fromtimestamp(self.env.now)
        yield self.env.timeout(1)

    def run(self):
        proc = self.env.process(self.step())
        self.env.run(until=proc)

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

    def is_valid_time(self, time_):
        if self.simulator is not None:
            return self.simulator.is_valid_time(time_)
        else:
            if time_ > datetime.now():
                return True
            return False

    def get_current_time(self):
        if self.simulator is not None:
            return self.simulator.get_current_time()
        else:
            return datetime.now()

    def get_current_timestamp(self):
        if self.simulator is not None:
            return TimeStamp.from_datetime(self.simulator.get_current_time())
        else:
            return TimeStamp()

    def init_ztp(self):
        midnight = self.get_current_time().replace(hour=0, minute=0, second=0, microsecond=0)
        ztp = TimeStamp()
        ztp.timestamp = midnight
        return ztp

    def run(self):
        if self.simulator is not None:
            self.simulator.run()
