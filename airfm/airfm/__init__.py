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

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')

FLAGS = gflags.FLAGS
gflags.DEFINE_string('mongo_host', '127.0.0.1', 'MongoDB host')
gflags.DEFINE_integer('mongo_port', 27017, 'MongoDB port')
gflags.DEFINE_string('host', '127.0.0.1', 'Server host')
gflags.DEFINE_integer('port', 8080, 'Server port')

def main():
    try:
        FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    app = create_app(mongo_host=FLAGS.mongo_host, mongo_port=FLAGS.mongo_port)
    server = WSGIServer((FLAGS.host, FLAGS.port), app)

    def shutdown():
        logging.warning('server shutdown')
        server.stop()
    gevent.signal(signal.SIGTERM, shutdown)

    try:
        logging.info("server running on %s:%d. pid %s", FLAGS.host, FLAGS.port, os.getpid())
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown()


if __name__ == '__main__':
    main()