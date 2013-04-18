#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()

import os
import sys
import gevent
import signal
import logging
import gflags
from gevent.wsgi import WSGIServer

from .comet import create_app

FLAGS = gflags.FLAGS
gflags.DEFINE_string('redis_host', '127.0.0.1', 'Redis host')
gflags.DEFINE_integer('redis_db', 0, 'Redis database')
gflags.DEFINE_string('host', '127.0.0.1', 'Server host')
gflags.DEFINE_integer('port', 6000, 'Server port')
gflags.DEFINE_integer('maxconn', 10000, 'Max connection limit')

def main():
    try:
        FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')

    app = create_app(redis_host=FLAGS.redis_host, redis_db=FLAGS.redis_db)
    server = WSGIServer((FLAGS.host, FLAGS.port), app, spawn=FLAGS.maxconn)

    def shutdown():
        logging.warning('server shutdown')
        server.stop()

    gevent.signal(signal.SIGTERM, shutdown)

    try:
        logging.info("server running on %s:%d. pid %s", FLAGS.host, FLAGS.port, os.getpid())
        gevent.spawn(app.service_visit)
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown()


if __name__ == '__main__':
    main()