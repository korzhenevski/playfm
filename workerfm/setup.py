#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='workerfm',
    version='0.2.0',
    author='RadioVoice',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'workerfm = workerfm.cli:main',
        ],
    },
)
