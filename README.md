
[![Build Status](https://travis-ci.com/anenriquez/mrta_allocation.svg?token=QudZDF4JraaUN8o4yWNo&branch=master)](https://travis-ci.com/anenriquez/mrta_allocation)

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



## Using Docker

[Install docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/)

[Install docker-compose](https://docs.docker.com/compose/install/)

docker-compose build task_allocation_test

docker-compose up -d robot

docker-compose up task_allocation_test


## Without Docker

Install the repositories

-  [mrta_stn](https://github.com/anenriquez/mrta_stn)

- [ropod_common](https://github.com/ropod-project/ropod_common)

- [mrta_datasets](https://github.com/anenriquez/mrta_datasets.git )


Get the requirements:
```
pip3 install -r requirements.txt
```

Add the task_allocation to your `PYTHONPATH` by running:

```
pip3 install --user -e .
```

Go to `/allocation` and run in a terminal

```
python3 robot.py ropod_001
```

Go to `/tests` and run test in another terminal
```
python3 task_allocator.py three_tasks.csv
```

## References

[1] E. Nunes, M. Gini. Multi-Robot Auctions for Allocation of Tasks with Temporal Constraints. Proceedings of the Twenty-Ninth AAAI Conference on Artificial Intelligence. 2015

[2] Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Conference on Artificial Intelligence (AAAI. 2017)

[3] Akmal et al. 2019. Quantifying Degrees of Controllability for Temporal Networks with Uncertainty. In Proc of the 29th International Conference on Automated Planning and Scheduling (ICAPS-2019). 