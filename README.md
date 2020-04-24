
[![Build Status](https://travis-ci.com/anenriquez/mrta.svg?branch=master)](https://travis-ci.com/anenriquez/mrta)

# Multi-Robot Task Allocation (MRTA)

Allocates tasks with temporal constraints and uncertain durations to a multi-robot system.

Includes three allocation algorithms:
- Temporal-sequential single item auctions (TeSSI)[1]. 
- Temporal-sequential single item auctions with degree of strong controllability (TeSSI-DSC) (based on [1] and [3]).
- Temporal-sequential single item auctions with static robust execution (TeSSI-SREA) (based on [1] and [2])
 
Each robot maintains a temporal network with its tasks.
The temporal network is either a:
- Simple Temporal Network (STN)
- Simple Temporal Network with Uncertainties (STNU)
- Probabilistic Simple Temporal Network (PSTN)

The temporal network represents a Simple Temporal Problem (STP).

The [mrta_stn](https://github.com/anenriquez/mrta_stn/) repository includes the temporal
network models and solvers for the STP.


The system consists of a fms (fleet managements system), a robot proxy and a robot instance per physical robot in the fleet.

Brief description of the components: 

![component_diagram](https://github.com/ropod-project/mrta/blob/develop/documentation/component_diagram.png)

### FMS: 
- Gets tasks' plan from pickup to delivery and adds it to the task.
- Requests the auctioneer to allocate tasks
 
#### Auctioneer
- Announces unallocated tasks to the robot proxies in the local network, opening an allocation round.
- Receives bids from the robot bidders.
- Elects a winner per allocation round or throws an exception indicating that no allocation was possible in the current round.

#### Dispatcher
- Gets earliest task and checks schedulability condition (a task is schedulable x time before its start time).
- Adds action between current robot's position and the task's pickup location.
- Dispatches a task queue to the schedule execution monitor. 

#### Timetable Monitor
- Receives task-status messages 
- Updates the corresponding robot's timetable accordingly and triggers recovery measures if necessary. 

#### Fleet Monitor
- Update robot's positions based on robot-pose messages.

#### PerformanceTracker
- Updates performance metrics during allocation, scheduling and execution

#### Simulator
- Controls simulation time using [simpy](https://simpy.readthedocs.io/en/latest/)

### RobotProxy
Acts on behalf of the robot

#### Bidder
- Receives task announcements.
- Computes a bid per task received in the task announcement. Bid calculation is dependant of the allocation method.
- Sends its best bid to the auctioneer.

#### Timetable Monitor
- Same as the timetable monitor, but only updates the robot's proxy timetable.

### Robot
Physical robot (in this case, just a mockup)

#### Schedule Monitor
- Receives a task queue and schedules the first task in the queue.
- Sends the task to the executor. 
- Receives task-status messages from the executor and monitors the execution of the task.
- Triggers recovery measures in case the current task violates the temporal constraints and the next task is at risk. 

#### Executor
- Determines the duration of actions based on a duration graph (travel time based on historical information) and sends task-status msgs.

#### API:
- Provides middleware functionality

#### ccu_store
- interface to interact with the ccu db

#### robot_store
- interface to interact with the robot db

#### robot_proxy_store
- interface to interact with the robot proxy db


# Installation

Create directory for logger
```
sudo mkdir -p /var/log/mrta
sudo chown -R $USER:$USER /var/log/mrta
```

Available approaches are specified in mrs/config/default/approaches.yaml

## Using Docker

[Install docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/)

[Install docker-compose](https://docs.docker.com/compose/install/)

Go to `mrs/tests` and run
```
python3 run.py approach_name

```

Example:

```
python3 run.py tessi-dsc-corrective-preempt
```

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

Open a terminal per robot proxy and run

```
python3 robot_proxy.py ropod_001 --approach approach_name
```

Open a terminal per robot and run

```
python3 robot.py ropod_001 --approach approach_name
```

Run in another terminal

```
python3 ccu.py  --approach approach_name
```

Go to `/tests` and run test in another terminal
```
python3 test.py --approach approach_name
```

## References

[1] E. Nunes, M. Gini. Multi-Robot Auctions for Allocation of Tasks with Temporal Constraints. Proceedings of the Twenty-Ninth AAAI Conference on Artificial Intelligence. 2015

[2] Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Conference on Artificial Intelligence (AAAI. 2017)

[3] Akmal et al. 2019. Quantifying Degrees of Controllability for Temporal Networks with Uncertainty. In Proc of the 29th International Conference on Automated Planning and Scheduling (ICAPS-2019). 