Configuration
==================

Parameters
---------------------------------

The MRS configuration file in YAML format is located at ``mrs/config/default/config.yaml`` and
includes the following parameters:

**Database names and ports**
::

    ccu_store:
      db_name: ccu_store
      port: 27017

    robot_proxy_store:
      db_name: robot_proxy_store
      port: 27017

    robot_store:
      db_name: robot_store
      port: 27017

**Simulator**
::
    simulator:
      initial_time: 2020-01-23T08:00:00.000000
      factor: 0.2

* initial time: datetime
* factor: time between each simulation step

**Fleet:** List of robot IDs in the fleet
::
    fleet:
      - robot_001
      - robot_002
      - robot_003
      - robot_004
      - robot_005

**Allocation Method:** Name of the allocation method to use
::
    allocation_method: tessi-srea

Options: tessi, tessi-srea, tessi-dsc

Note: To use TeSSI-DREA, choose tessi-srea and set the d graph watchdog to true.

**Planner**
::
    planner:
      map_name: brsu

map_name: Name of the duration graph used by the planner.

**Delay recovery**
::
    delay_recovery:
      type_: corrective
      method: re-allocate

type\_:

    * Corrective: Checks if a recovery method is required only if the last assignment was inconsistent.
    * Preventive: Checks if a recovery method is required both, when the last assignment was consistent and when it was inconsistent.

method: Recovery method to use. Options: re-allocate, preempt

**Auctioneer**
::
    auctioneer:
      closure_window: 1
      alternative_timeslots: False

* closure\_window: Time (in minutes) between the earliest pickup time of the earliest task in an allocation round and the round closure time.

* alternative\_timeslots: If true, set task constraints to soft when no robots could bid for the task.

**Dispatcher**
::
    dispatcher:
      freeze_window: 0.1
      n_queued_tasks: 3

* freeze\_window:  Time (in minutes) before the task’s earliest start time at which the task will be dispatched.
* n\_queued\_tasks: Number of tasks in the task queue.

**Bidder**
::
    bidder:
      bidding_rule: completion_time
      auctioneer_name: fms_zyre_api

* bidding rule: Name of the bidding rule robots use to compute their bids.
* auctioneer name: Name of the auctioneer’s Zyre node.

**Executor**
::
    executor:
      max_seed: 2147483647
      map_name: brsu

* max seed. Seed for the random number generator.
* map name. Name of the duration graph used by the mockup executor to determine action task duration.

**Scheduler**
::
    scheduler:
      time_resolution: 0.5 # minutes

time_resolution: Time resolution (in minutes) between the task’s earliest and latest start
time.

**Middleware API:** Zyre configuration for the FMS, the robot proxies and the robots.
::
    robot_proxy_api:
      version: 0.1.0
      middleware:
        - zyre
      zyre:
        zyre_node:
          node_name: robot_id_proxy
          interface: null
          groups:
            - TASK-ALLOCATION
          message_types:
            - TASK
            - TASK-ANNOUNCEMENT
            - TASK-CONTRACT
            - TASK-CONTRACT-CANCELLATION
            - ROBOT-POSE
            - TASK-STATUS
            - REMOVE-TASK-FROM-SCHEDULE
          debug_msgs: false
        acknowledge: false
        publish:
          bid:
            groups: ['TASK-ALLOCATION']
            msg_type: 'BID'
            method: whisper
          no-bid:
            groups: ['TASK-ALLOCATION']
            msg_type: 'NO-BID'
            method: whisper
          task-contract-acknowledgement:
            groups: ['TASK-ALLOCATION']
            msg_type: 'TASK-CONTRACT-ACKNOWLEDGEMENT'
            method: shout
          robot-pose:
            groups: ['TASK-ALLOCATION']
            msg_type: 'ROBOT-POSE'
            method: shout
        callbacks:
          - msg_type: 'TASK-ANNOUNCEMENT'
            component: 'bidder.task_announcement_cb'
          - msg_type: 'TASK-CONTRACT'
            component: 'bidder.task_contract_cb'
          - msg_type: 'TASK-CONTRACT-CANCELLATION'
            component: 'bidder.task_contract_cancellation_cb'
          - msg_type: 'ROBOT-POSE'
            component: '.robot_pose_cb'
          - msg_type: 'REMOVE-TASK-FROM-SCHEDULE'
            component: '.remove_task_cb'
          - msg_type: 'TASK'
            component: '.task_cb'
          - msg_type: 'TASK-STATUS'
            component: '.task_status_cb'

* node\_name: Name of the Zyre node.
* groups: Name of the groups the node belongs to.
* message types: Name of the messages the node listens to.

Publish configuration:
- msg\_type: Name of the message.
- groups: Groups to publish.
- method: Method used ot publish, can be shout or whisper.

Callbacks configuration:
- msg\_type: Name of the message.
- component: Component that implements the callback.

**Logger:** Includes formatters, handlers, and loggers.
::

    logger:
      version: 1
      formatters:
        default:
          format: '[%(levelname)-5.5s]  %(asctime)s [%(name)-35.35s] %(message)s'
          datefmt: '%Y-%m-%d %H:%M:%S'
      handlers:
        console:
          class: ropod.utils.logging.color.ColorizingStreamHandler
          level: DEBUG
          formatter: default
          stream: ext://sys.stdout
        file:
          class: logging.handlers.TimedRotatingFileHandler
          level: DEBUG
          formatter: default
          filename: /var/log/mrta/fms.log
          when: 'm'
          interval: 5
      loggers:
        mrs:
          level: DEBUG
      root:
        level: DEBUG
        handlers: [console, file]

