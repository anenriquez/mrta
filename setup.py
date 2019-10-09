#!/usr/bin/env python

from setuptools import setup

setup(name='mrs',
      packages=['mrs', 'mrs.config', 'mrs.config.builders', 'mrs.db.models', 'mrs.db.models.performance',
                'mrs.db.queries', 'mrs.structs', 'mrs.utils', 'mrs.exceptions', 'mrs.task_allocation',
                'mrs.task_execution', 'mrs.experiments', 'mrs.tests'],
      version='0.2.0',
      description='Multi-Robot System (MRS) components for performing'
                  'Multi-Robot Task Allocation (MRTA) and executing'
                  'tasks with temporal constraints and uncertain '
                  'durations',
      author='Angela Enriquez Gomez',
      author_email='angela.enriquez@smail.inf.h-brs.de',
      package_dir={'': '.'}
      )
