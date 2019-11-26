
[![Build Status](https://travis-ci.com/anenriquez/mrta.svg?branch=master)](https://travis-ci.com/anenriquez/mrta)

# Multi-Robot Task Allocation (MRTA)

Allocates tasks with temporal constraints and uncertain durations to a multi-robot system.
 
Uses an auction-based approach based on [1]. 

Each robot maintains a temporal network with its tasks.
The temporal network is either a:
- Simple Temporal Network (STN)
- Simple Temporal Network with Uncertainties (STNU)
- Probabilistic Simple Temporal Network (PSTN)

The temporal network represents a Simple Temporal Problem (STP).

The [mrta_stn](https://github.com/anenriquez/mrta_stn/) repository includes the temporal
network models and solvers for the STP.


The bidding rule is a combination of two metrics of the temporal network.
- Robustness
- Temporal

Configure the robustness and temporal parameters in `config/config.yaml`

The robustness metric is a result of the STP solver and can take the values:

- fpc
- srea      [2]
- dsc_lp    [3]

The temporal metric measures a value of the dispatching graph (result of solving the STP).
It can take the values:

- completion_time
- makespan

## Component Diagram

The system consists of a ccu (central control unit) and a robot instance per physical robot in the fleet.

![component_diagram](https://github.com/anenriquez/mrta/blob/feature/schedule-monitor/documentation/component_diagram.png)

Brief description of the components: 

#### Auctioneer
- Announces unallocated tasks to the robots in the local network, opening an allocation round.
- Receives bids from the robot bidders.
- Elects a winner per allocation round or throws an exception indicating that no allocation was possible in the current round.

#### Dispatcher
-  Receives requests for a DISPATCH-QUEUE-UPDATE.
- Creates a dispatchable graph with two tasks and checks its consistency.
-  If the graph is consistent, creates a DISPATCH-QUEUE-UPDATE message and sends it to the Schedule Monitor. 

#### Bidder
- Receives task announcements.
- Computes a bid per task received in the task announcement. Bid calculation is dependant of the allocation method.
- Sends its best bid to the auctioneer.

#### Schedule Monitor
- Requests DISPATCH-QUEUE-UPDATEs to the Dispatcher.
- Gets the earliest task in the DISPATCH-QUEUE-UPDATE message and checks if it is schedulable.
- Requests the Scheduler to schedule the task. 
- Sends the the task to the Executor Interface.
- Applies corrective measures (if included in the config file).
 
#### Scheduler
- Instantiates the pre-condition start time of a task in an STN and checks the consistency of the resulting temporal network.
-  If the network is consistent, sets the pre-condition start time of the task. 

#### Executor Interface
- Receives a Task from the Schedule Monitor.
- Once the current time is equal to the start time of the task, sends the task to the Executor.

All of the above components make use of the API object. The ccu components make use of the ccu_store object and the robot components use the robot_store component

#### API:
- Provides middleware functionality

#### ccu_store
- interface to interact with the ccu db

#### robot_store
- interface to interact with the robot db





# Installation

Create directory for logger
```
sudo mkdir -p /var/log/mrta
sudo chown -R $USER:$USER /var/log/mrta
```


## Using Docker

[Install docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/)

[Install docker-compose](https://docs.docker.com/compose/install/)

docker-compose build task_allocation_test

docker-compose up -d robot

docker-compose up -d ccu 

docker-compose up task_allocation_test


## Without Docker

Install the repositories

-  [mrta_stn](https://github.com/anenriquez/mrta_stn)

- [ropod_common](https://github.com/ropod-project/ropod_common)


Get the requirements:
```
pip3 install -r requirements.txt
```

Add the task_allocation to your `PYTHONPATH` by running:

```
pip3 install --user -e .
```

Go to `/mrs` and run in a terminal

```
python3 robot.py ropod_001
```

Run in another terminal

```
python3 ccu.py
```

Go to `/tests` and run test in another terminal
```
python3 allocation_test.py 
```

## References

[1] E. Nunes, M. Gini. Multi-Robot Auctions for Allocation of Tasks with Temporal Constraints. Proceedings of the Twenty-Ninth AAAI Conference on Artificial Intelligence. 2015

[2] Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Conference on Artificial Intelligence (AAAI. 2017)

[3] Akmal et al. 2019. Quantifying Degrees of Controllability for Temporal Networks with Uncertainty. In Proc of the 29th International Conference on Automated Planning and Scheduling (ICAPS-2019). 