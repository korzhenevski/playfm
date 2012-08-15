# -*- coding: utf-8 -*-

from gevent.monkey import patch_all
patch_all()
from rvlib import cli_bootstrap
from .worker import Worker

def main():
    config = cli_bootstrap(__name__, description='Radio platform worker')
    worker = Worker(endpoint=dict(config.items('endpoint')),
                    maxjobs=config.getint('worker', 'maxjobs'))
    worker.run()

