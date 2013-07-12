#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='cometfm',
    version='0.1.0',
    author='RadioVoice',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[
        'Jinja2==2.7',
        'Werkzeug==0.9.1',
        'gevent==0.13.8',
        'psutil==1.0.0',
        'python-gflags==2.0',
        'redis==2.7.6',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'cometfm = cometfm.__main__:main',
        ],
    },
)
