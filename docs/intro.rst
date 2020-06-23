Multi-Robot Task Allocation (MRTA)
==================================================


Allocates tasks with temporal constraints and uncertain durations to a multi-robot system.

Includes four MRTA algorithms:

* Temporal-sequential single item auctions with static robust execution (TeSSI-SREA) (based on [1] and [2])
* Temporal-sequential single item auctions with dynamic robust execution (TeSSI-DREA) (based on [1] and [2])
* Temporal-sequential single item auctions with degree of strong controllability (TeSSI-DSC) (based on [1] and [3]).
* Temporal-sequential single item auctions (TeSSI)[1].

Robots add their tasks to a timetable, which includes:

* stn: Temporal Network of type STN, STNU or PSTN depending on the algorithm.
* dispatchable graph: Space of solutions of the temporal network.

The temporal network is either a:

- Simple Temporal Network (STN)[4]
- Simple Temporal Network with Uncertainties (STNU)[5]
- Probabilistic Simple Temporal Network (PSTN)[6]

.. list-table:: MRTA algorithms
   :widths: 25 25 50
   :header-rows: 1

   * - Algorithm
     - Temporal Network
     - Simple Temporal Solver
   * - TeSSI-SREA
     - PSTN
     - Static Robust Execution Algorithm (SREA)
   * - TeSSI-DREA
     - PSTN
     - Dynamic Robust Execution Algorithm (SREA)
   * - TeSSI-DSC
     - STNU
     - Degree of Strong Controllability Linar Program (DSC-LP)
   * - TeSSI
     - STN
     - Floyd-Warshall Algorithm


Architecture
-------------
.. figure:: /images/mrs.png
    :align: center

    MRS component diagram

The MRS architecture is based on the `ROPOD FMS architecture
<https://git.ropod.org/ropod/ccu/fleet-management>`_

******************************
Fleet Management System (FMS)
******************************

    * Gets tasks' plan from pickup to delivery and adds it to the task.
    * Requests the auctioneer to allocate tasks

    **Auctioneer**
        * Announces unallocated tasks to the robot proxies in the local network, opening an allocation round.
        * Receives bids from the robot bidders.
        * Elects a winner per allocation round or logs a message indicating that no allocation was possible in the current round.

    **Dispatcher**
        * Gets earliest task and checks schedulability condition (a task is schedulable *x* time before its start time).
        * Adds action between current robot's position and the task's pickup location.
        * Dispatches a task queue to the schedule execution monitor.

    **Timetable Monitor**
        * Receives task-status messages
        * Updates the corresponding robot's timetable accordingly and triggers recovery measures if necessary.

    **Fleet Monitor**
        * Update robot's positions based on robot-pose messages.

    **PerformanceTracker**
        * Updates performance metrics during allocation, scheduling and execution

    **Simulator**
        * Controls simulation time using `simpy <https://simpy.readthedocs.io/en/latest/>`_

    **ccu_store**
        * interface to interact with the ccu db

**************
Robot Proxy
**************
Acts on behalf of the robot

    **Bidder**
        * Receives task announcements.
        * Computes a bid per task received in the task announcement. Bid calculation is dependant of the allocation method.
        * Sends its best bid to the auctioneer.

    **Timetable Monitor**
        * Same as the timetable monitor, but only updates the robot's proxy timetable.

    **robot_proxy_store**
        * interface to interact with the robot proxy db

*******
Robot
*******
Components running in the physical robot (in this case, just a mockup)

    **Schedule Monitor**
        * Receives a task queue and schedules the first task in the queue.
        * Sends the task to the executor.
        * Receives task-status messages from the executor and monitors the execution of the task.
        * Triggers recovery measures in case the current task violates the temporal constraints and the next task is at risk.

    **Executor**
        * Determines the duration of actions based on a duration graph (travel time based on historical information) and sends task-status msgs.

    **robot_store**
        * interface to interact with the robot db

Components communicate via `Zyre <https://github.com/zeromq/zyre>`_


References
^^^^^^^^^^^^^^^^^

[1] E. Nunes, M. Gini. Multi-Robot Auctions for Allocation of Tasks with Temporal Constraints. Proceedings of the Twenty-Ninth AAAI Conference on Artificial Intelligence. 2015

[2] Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Lund et al. 2017. Robust Execution of Probabilistic Temporal Plans. In Proc. of the 31th Conference on Artificial Intelligence (AAAI. 2017)

[3] Akmal et al. 2019. Quantifying Degrees of Controllability for Temporal Networks with Uncertainty. In Proc of the 29th International Conference on Automated Planning and Scheduling (ICAPS-2019).

[4] Rina Detcher, Itay Meiri, and Judea Pearl. Temporal Constraint Networks. Knowledge Representation, 49:61–95, 1991.

[5] Thierry Vidal. Handling Contingency in Temporal Constraint Networks: from Consistency to Controllabilities. Journal of Experimental & Theoretical Artificial Intelligence, 11(1):23–45, 1999.

[6] Ioannis Tsamardinos. A Probabilistic Approach to Robust Execution of Temporal Plans with Uncertainty. In Methods and Applications of Artificial Intelligence, pages 97–108. Springer Verlag, 2002.
