#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='ester',
    version='0.2.0',
    author='RadioVoice',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[
        'gevent==0.13.8',
        'hiredis==0.1.1',
        'python-gflags==2.0',
        'redis==2.6.0',
        'zerorpc==0.4.1',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'ester = ester.__main__:main',
        ],
    },
)
