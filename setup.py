#!/usr/bin/env python

from setuptools import setup

setup(name='mrs',
      packages=['mrs',
                'mrs.config',
                'mrs.config.default',
                'mrs.db.models',
                'mrs.exceptions',
                'mrs.allocation',
                'mrs.tests',
                'mrs.messages',
                'mrs.timetable',
                'mrs.dispatching',
                'mrs.execution',
                'mrs.simulation',
                'mrs.utils'],
      version='0.2.0',
      description='Multi-Robot System (MRS) components for performing'
                  'Multi-Robot Task Allocation (MRTA) and executing'
                  'tasks with temporal constraints and uncertain '
                  'durations',
      author='Angela Enriquez Gomez',
      author_email='angela.enriquez@smail.inf.h-brs.de',
      package_dir={'': '.'}
      )
