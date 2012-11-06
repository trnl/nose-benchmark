# -*- coding: utf-8 -*-
"""
Benchmark plugin.

"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='nose-benchmark',
    version='0.9.3',
    author='Nikita Basalaev',
    author_email = 'nikita@mail.by',
    description = 'Benchmark nose plugin',
    license = 'GNU LGPL',
    py_modules = ['benchmark'],
    entry_points = {
        'nose.plugins.0.10': [
            'benchmark = benchmark:Benchmark'
            ]
        }
    )
