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
        'pyzmq==2.2.0.1',
        'gevent==0.13.8',
        'hiredis==0.1.1',
        'pymongo==2.5',
        'python-gflags==2.0',
        'redis==2.6.0',
        'ujson==1.30',
        'zerorpc==0.4.1',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'managerfm = managerfm.__main__:main',
        ],
    },
)
