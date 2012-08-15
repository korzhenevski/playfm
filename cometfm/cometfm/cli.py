#!/usr/bin/env python
import gevent
from gevent import monkey
monkey.patch_all()
from gevent.wsgi import WSGIServer

import os
import signal
import logging
from redis import Redis
from .cometfm import Server
from .app import app
from rvlib import cli_bootstrap

def main():
    config = cli_bootstrap(__name__, description='Comet server')

    redis = Redis(host=config.get('redis', 'host'), db=config.getint('redis', 'database'))
    app.cometfm = Server(redis=redis, endpoint=dict(config.items('endpoint')))
    app.cometfm.run()

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