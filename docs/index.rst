.. mrta documentation master file, created by
   sphinx-quickstart on Mon Jun 22 13:21:51 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to mrta's documentation!
================================

The mrta includes algorithms to allocate tasks to a fleet of robots, along with a Multi-Robot System architecture
(based on the ROPOD FMS architecture) to allocate, schedule and monitor robot schedules. For more information about the
architecture see :doc:`intro`.


.. toctree::
   :name: tocmain
   :caption: Overview
   :hidden:
   :glob:
   :maxdepth: 2

   Intro <intro>
   Modules <mrs>

Getting started
================

Without Docker
^^^^^^^^^^^^^^^^^

Install the repositiories:

- `ropod_common <https://github.com/ropod-project/ropod_common>`_

- `mrta_datasets <https://github.com/anenriquez/mrta_datasets)>`_

- `mrta_planner <https://github.com/anenriquez/mrta_planner)>`_

Create directory for logger::

   sudo mkdir -p /var/log/mrta
   sudo chown -R $USER:$USER /var/log/mrta



Get the mrta requirements::

   pip3 install -r requirements.txt

Add mrta to your PYTHONPATH::

   pip3 install --user -e .


Instructions for running experiments:

Open a terminal per robot proxy and run::

 python3 robot_proxy.py robot_id --file config_file --experiment experiment_name --approach approach_name

Example::

   python3 robot_proxy.py robot_001 --experiment non_intentional_delays --approach tessi-corrective-re-allocate

Open a terminal per robot and run::

   python3 robot.py robot_id --file config_file --experiment experiment_name --approach approach_name


Example::

   python3 robot.py robot_001 --experiment non_intentional_delays --approach tessi-corrective-re-allocate

Open a terminal and start the ccu::

   python3 ccu.py --experiment experiment_name --approach approach_name

Example::

   python3 ccu.py --experiment non_intentional_delays --approach tessi-corrective-re-allocate

By default, uses the configuration file ``mrs/config/default/config.yaml``.

With Docker
^^^^^^^^^^^^^^^^^

- `Install docker <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`_

- `Install docker-compose <https://docs.docker.com/compose/install/>`_

Add mrta to your PYTHONPATH::

   pip3 install --user -e .


Instructions for running experiments:

Go to `experiments/run` and run::

   python3 run_approach.py experiment_name approach_name number_of_runs

Example::

   python3 run_approach.py non_intentional_delays tessi-corrective-re-allocate 10


Available approaches are specified in ``mrs/config/default/approaches.yaml``

Available experiments are specified in ``mrs/experiments/config/config.yaml``

Robot initial poses are specified in ``mrs/experiments/config/poses/robot_init_poses.yaml``

