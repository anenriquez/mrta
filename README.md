[![Build Status](https://travis-ci.com/anenriquez/mrta_allocation.svg?token=QudZDF4JraaUN8o4yWNo&branch=master)](https://travis-ci.com/anenriquez/mrta_allocation)

# Multi-Robot Task Allocation (MRTA)

## Installation

Install the repositories:

-  [mrta_temporal_models](https://github.com/anenriquez/mrta_temporal_models)

- [ropod_common](https://github.com/ropod-project/ropod_common)


Get the requirements:
```
pip3 install -r requirements.txt
```

Add the task_allocation to your `PYTHONPATH` by running:

```
sudo pip3 install -e .
```

## Config file

Change the scheduling method in `config/config.yaml`.

Possible scheduling methods:
- srea
- fpc
- dsc_lp

## Usage

Go to `/allocation` and run in a terminal

```
python3 robot.py ropod_001
```

Go to `/allocation` and run in a terminal
```
python3 auctioneer.py
```
Go to `/tests` and run test in another terminal
```
python3 two_tasks_test.py
```

## References

E. Nunes, M. Gini. Multi-Robot Auctions for Allocation of Tasks with Temporal Constraints. Proceedings of the Twenty-Ninth AAAI Conference on Artificial Intelligence. 2015
