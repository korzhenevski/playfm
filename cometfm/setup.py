#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='cometfm',
    version='0.1.0',
    author='RadioVoice',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'cometfm = cometfm:main',
        ],
    },
)
