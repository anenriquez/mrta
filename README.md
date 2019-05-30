[![Build Status](https://travis-ci.com/anenriquez/mrta_allocation.svg?token=QudZDF4JraaUN8o4yWNo&branch=master)](https://travis-ci.com/anenriquez/mrta_allocation)

# Multi-Robot Task Allocation (MRTA)

## Installation

Install the repository [mrta_temporal_models](https://github.com/anenriquez/mrta_temporal_models)


Get the requirements:
```
pip3 install -r requirements.txt
```

Add the task_allocation to your `PYTHONPATH` by running:

```
sudo pip3 install -e .
```

## Usage

Start a robot in a terminal
```
python3 robot.py ropod_001
```

Start the auctioneer in another terminal
```
python3 auctioneer.py
```
Run the task_allocator in another terminal
```
python3 task_allocator.py
```

## References

E. Nunes, M. Gini. Multi-Robot Auctions for Allocation of Tasks with Temporal Constraints. Proceedings of the Twenty-Ninth AAAI Conference on Artificial Intelligence. 2015
