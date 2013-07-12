#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='managerfm',
    version='0.1.0',
    author='RadioVoice',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[
        'gevent==0.13.8',
        'pymongo==2.5.2',
        'python-gflags==2.0',
        'redis==2.7.6',
        'ujson==1.33',
        'zerorpc==0.4.3',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'managerfm = managerfm.__main__:main',
        ],
    },
)
