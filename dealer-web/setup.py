#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="dealer-web",
    version="0.0.1",
    author="again.fm",
    author_email="team@again.fm",
    packages=find_packages(),
    install_requires=[
        'gevent',
        'protobuf',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': ['dealer-web = dealer_web:main'],
    },
)
