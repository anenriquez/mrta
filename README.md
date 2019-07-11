[![Build Status](https://travis-ci.com/anenriquez/mrta_allocation.svg?token=QudZDF4JraaUN8o4yWNo&branch=master)](https://travis-ci.com/anenriquez/mrta_allocation)

# Multi-Robot Task Allocation (MRTA)

## Installation

Install the repositories:

-  [mrta_stn](https://github.com/anenriquez/mrta_stn)

- [ropod_common](https://github.com/ropod-project/ropod_common)

- [mrta_datasets](https://github.com/anenriquez/mrta_datasets.git )


Get the requirements:
```
pip3 install -r requirements.txt
```

Add the task_allocation to your `PYTHONPATH` by running:

```
sudo pip3 install -e .
```

## Config file

Change the stp method in `config/config.yaml`.

Possible scheduling methods:
- srea
- fpc
- dsc_lp

## Usage

Go to `/allocation` and run in a terminal

```
python3 robot.py ropod_001
```

Go to `/tests` and run test in another terminal
```
python3 task_allocator.py three_tasks.csv
```

## References

E. Nunes, M. Gini. Multi-Robot Auctions for Allocation of Tasks with Temporal Constraints. Proceedings of the Twenty-Ninth AAAI Conference on Artificial Intelligence. 2015
