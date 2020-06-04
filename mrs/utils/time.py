from ropod.utils.timestamp import TimeStamp
from datetime import datetime, timedelta


def relative_to_ztp(ztp, time_, resolution="seconds"):
    """Returns the relative time between the given time_ (datetime) and the ztp (TimeStamp)"""
    if time_.isoformat().startswith("9999-12-31T"):
        r_time = float('inf')
    else:
        r_time = TimeStamp.from_datetime(time_).get_difference(ztp, resolution)
    return r_time


def to_timestamp(ztp, r_time):
    """ Returns a timestamp ztp(TimeStamp) + relative time(float) in seconds
    """
    if r_time == float('inf'):
        time_ = TimeStamp()
        time_.timestamp = datetime.max
    else:
        time_ = ztp + timedelta(seconds=r_time)
    return time_

