from ropod.utils.timestamp import TimeStamp
from datetime import timedelta


if __name__ == '__main__':

    # open_time = TimeStamp()
    # print("open time: ", open_time)
    # print(type(open_time))
    #
    # round_time = timedelta(minutes=15)
    # closure_time = TimeStamp(round_time)
    #
    # print("closure time: ", closure_time)
    # print(type(closure_time))
    #
    # difference = closure_time.get_difference(open_time, resolution='hours')
    # print("Difference: ", difference)
    # print(type(difference))

    delta = timedelta(minutes=1)
    earliest_start_time = TimeStamp(delta)
    print(earliest_start_time)
    print(earliest_start_time.timestamp)
    print(type(earliest_start_time.timestamp))
