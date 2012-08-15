# -*- coding: utf-8 -*-

from gevent.monkey import patch_all
patch_all()
from rvlib import cli_bootstrap
from .worker import Worker

def main():
    """
    import gevent
    from .worker import WorkerThread, MockManager
    manager = MockManager()
    r = WorkerThread(job_id=1, url='http://ru.ah.fm/', manager=manager)
    def stop_r():
        print 'stop'
        r.stop()
    gevent.spawn_later(1, stop_r)
    r.run()
    """
    config = cli_bootstrap(__name__, description='Radio platform worker')
    worker = Worker(endpoint=dict(config.items('endpoint')),
                    maxjobs=config.getint('worker', 'maxjobs'))
    worker.run()

