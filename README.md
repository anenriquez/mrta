
[![Build Status](https://travis-ci.com/anenriquez/mrta.svg?branch=master)](https://travis-ci.com/anenriquez/mrta)

# Multi-Robot Task Allocation (MRTA)

Allocates tasks with temporal constraints and uncertain durations to a multi-robot system.

Includes four allocation algorithms:
- Temporal Sequential Single-Item auctions (TeSSI)[1]. 
- Temporal Sequential Single-Item auctions with Degree of Strong Controllability (TeSSI-DSC) (based on [1] and [3]).
- Temporal Sequential Single-Item auctions with Static Robust Execution Algorithm (TeSSI-SREA) (based on [1] and [2])
- Temporal Sequential Single-Item auctions with Dynamic Robust Execution Algorithm (TeSSI-DREA) (based on [1] and [2])
 
Each robot maintains a temporal network with its tasks. The temporal network is either a:
- Simple Temporal Network (STN)
- Simple Temporal Network with Uncertainties (STNU)
- Probabilistic Simple Temporal Network (PSTN)

The temporal network represents a Simple Temporal Problem (STP).

The allocation methods can be combined with the delay recovery methods:
- preemption
- re-allocation
- relaxation of constraints

The [mrta_stn](https://github.com/anenriquez/mrta_stn/) repository includes the temporal
network models and solvers for the STP.

The system consists of a FMS (Fleet Managements System), a RobotProxy and a Robot instance per physical robot in the fleet.

Brief description of the components: 

![component_diagram](https://github.com/anenriquez/mrta/blob/master/documentation/mrs.png)

### FMS: 
- Gets tasks' plan from pickup to delivery and adds it to the task.
- Requests the auctioneer to allocate tasks.
 
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
- Controls simulation time using [simpy](https://simpy.readthedocs.io/en/latest/).

### RobotProxy
Acts on behalf of the robot.

#### Bidder
- Receives task announcements.
- Computes a bid per task received in the task announcement. Bid calculation is dependant of the allocation method.
- Sends its best bid to the auctioneer.

#### Timetable Monitor
- Same as the timetable monitor, but only updates the robot's proxy timetable.

### Robot
Physical robot (in this case, just a mockup).

#### Schedule Monitor
- Receives a task queue and schedules the first task in the queue.
- Sends the task to the executor. 
- Receives task-status messages from the executor and monitors the execution of the task.
- Triggers recovery measures in case the current task violates the temporal constraints and the next task is at risk. 

#### Executor
- Determines the duration of actions based on a duration graph (travel time based on historical information) and sends task-status msgs.

#### API:
- Provides middleware functionality.

#### ccu_store
- interface to interact with the ccu db.

#### robot_store
- interface to interact with the robot db.

#### robot_proxy_store
- interface to interact with the robot proxy db.

## Installation

### Without Docker

Install the repositiories:
- [ropod_common](https://github.com/ropod-project/ropod_common)
- [mrta_datasets](https://github.com/anenriquez/mrta_datasets)
- [mrta_planner](https://github.com/anenriquez/mrta_planner)

Create directory for logger
```
sudo mkdir -p /var/log/mrta
sudo chown -R $USER:$USER /var/log/mrta
```

Get the mrta requirements: 
```
pip3 install -r requirements.txt
```
Add mrta to your PYTHONPATH: 
```
pip3 install --user -e .
```

Instructions for running experiments:

Open a terminal per robot proxy and run:
```
 python3 robot_proxy.py robot_id --file config_file --experiment experiment_name --approach approach_name
```
Example: 
```
python3 robot_proxy.py robot_001 --experiment non_intentional_delays --approach tessi-corrective-re-allocate
```
Open a terminal per robot and run: 
	
```
python3 robot.py robot_id --file config_file --experiment experiment_name --approach approach_name
```
	
Example:
```
python3 robot.py robot_001 --experiment non_intentional_delays --approach tessi-corrective-re-allocate
```
Open a terminal and start the ccu: 

```
python3 ccu.py --experiment experiment_name --approach approach_name
```
Example: 
```	
python3 ccu.py --experiment non_intentional_delays --approach tessi-corrective-re-allocate
```

By default, uses the configuration file `mrs/config/default/config.yaml`.

## With Docker

- [Install docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/)

- [Install docker-compose](https://docs.docker.com/compose/install/)

Add mrta to your PYTHONPATH: 
```
pip3 install --user -e .
```

Instructions for running experiments:

Go to `experiments/run` and run: 
```	
python3 run_approach.py experiment_name approach_name number_of_runs
```
Example:
```	
python3 run_approach.py non_intentional_delays tessi-corrective-re-allocate 10
```

Available approaches are specified in `mrs/config/default/approaches.yaml`

Available experiments are specified in `mrs/experiments/config/config.yaml`

Robot initial poses are specified in `mrs/experiments/config/poses/robot_init_poses.yaml`


## References

[1] E. Nunes, M. Gini. Multi-Robot Auctions for Allocation of Tasks with Temporal Constraints. Proceedings of the Twenty-Ninth AAAI Conference on Artificial Intelligence. 2015

[2] Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Conference on Artificial Intelligence (AAAI. 2017)

[3] Akmal et al. 2019. Quantifying Degrees of Controllability for Temporal Networks with Uncertainty. In Proc of the 29th International Conference on Automated Planning and Scheduling (ICAPS-2019). 
