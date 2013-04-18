#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent.monkey import patch_all
patch_all()

import gevent
import gflags
import zerorpc
import sys
import logging
from .worker import Worker, VolumeMonitor
from pprint import pprint as pp
from time import time

FLAGS = gflags.FLAGS
gflags.DEFINE_string('manager', 'tcp://127.0.0.1:4242', 'Manager ZMQ address')
gflags.DEFINE_string('volumes', '/tmp/record', 'Storage volumes location')
gflags.DEFINE_integer('threads', 1, 'Max worker task threads')

def main():
    try:
        FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')

    manager = zerorpc.Client(FLAGS.manager)
    worker = Worker(manager)
    volume_monitor = VolumeMonitor(FLAGS.volumes, manager)
    gevent.joinall([
        gevent.spawn(worker.run, pool_size=FLAGS.threads),
        gevent.spawn(volume_monitor.monitor)
    ])

if __name__ == '__main__':
    main()