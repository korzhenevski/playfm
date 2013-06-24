#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent.monkey import patch_all
patch_all()

import gevent
import gflags
import zerorpc
import sys
import logging
from .worker import Worker


FLAGS = gflags.FLAGS
gflags.DEFINE_string('manager', 'tcp://127.0.0.1:4242', 'Manager ZMQ address')
gflags.DEFINE_string('record_to', '/tmp/record', 'Record files path')
gflags.DEFINE_integer('threads', 10, 'Max worker task threads')


def main():
    try:
        FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')

    manager = zerorpc.Client(FLAGS.manager)
    worker = Worker(manager, FLAGS.record_to)
    gevent.joinall([
        gevent.spawn(worker.run, pool_size=FLAGS.threads),
    ])

if __name__ == '__main__':
    main()