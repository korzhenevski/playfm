#!/usr/bin/env python
import gevent
import pymongo
from gevent import monkey
monkey.patch_all()
from gevent.wsgi import WSGIServer

import os
import signal
import logging
from .app import app, build_index_in_background
from rvlib import cli_bootstrap

def main():
    config = cli_bootstrap(__name__, description='Search server')

    db = pymongo.Connection(host=config.get('mongodb', 'host'))[config.get('mongodb', 'database')]

    gevent.spawn(build_index_in_background, db[config.get('mongodb', 'collection')])

    address = (config.get('server', 'host'), config.getint('server', 'port'))
    server = WSGIServer(address, app, log=None)

    def shutdown():
        logging.warning('shutdown server')
        server.stop()

    gevent.signal(signal.SIGTERM, shutdown)
    gevent.signal(signal.SIGINT, shutdown)

    try:
        logging.info("server running on %s:%d. pid %s", address[0], address[1], os.getpid())
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown()