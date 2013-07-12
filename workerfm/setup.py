#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='workerfm',
    version='0.2.0',
    author='RadioVoice',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[
        'gevent==0.13.8',
        'psutil==1.0.0',
        'python-gflags==2.0',
        'zerorpc==0.4.3',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'workerfm = workerfm.__main__:main',
        ],
    },
)
