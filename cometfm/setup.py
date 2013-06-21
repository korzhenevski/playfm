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
        'Jinja2==2.6',
        'Werkzeug==0.8.3',
        'gevent==0.13.8',
        'hiredis==0.1.1',
        'psutil==0.7.0',
        'python-gflags==2.0',
        'redis==2.6.0',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'cometfm = cometfm.__main__:main',
        ],
    },
)
