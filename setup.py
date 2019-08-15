#!/usr/bin/env python

from setuptools import setup

setup(name='mrs',
      packages=['mrs', 'mrs.config', 'mrs.utils', 'mrs.exceptions', 'mrs.task_allocation',
                'mrs.task_execution', 'mrs.task_execution.dispatching'],
      version='0.1.0',
      install_requires=[
            'numpy'
      ],
      dependency_links=['git+https://github.com/anenriquez/mrta_stn.git#egg=stn'],
      description='Multi-Robot System (MRS) components for performing'
                  'Multi-Robot Task Allocation (MRTA) and executing'
                  'tasks with temporal constraints and uncertain '
                  'durations',
      author='Angela Enriquez Gomez',
      author_email='angela.enriquez@smail.inf.h-brs.de',
      package_dir={'': '.'}
      )
