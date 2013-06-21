#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent.monkey import patch_all
patch_all()

import gevent
import gflags
import zerorpc
import logging
import sys
from .ester import Ester
from redis import Redis

FLAGS = gflags.FLAGS
gflags.DEFINE_string('manager', 'tcp://127.0.0.1:4242', 'Manager endpoint')
gflags.DEFINE_string('redis', '127.0.0.1', 'Redis host')
gflags.DEFINE_integer('redis_db', 0, 'Redis database')


def main():
    try:
        FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')

    manager = zerorpc.Client(FLAGS.manager)
    logging.info('connect to %s', FLAGS.manager)
    redis = Redis(host=FLAGS.redis, db=FLAGS.redis_db)
    ester = Ester(manager, redis)

    gevent.joinall([
        gevent.spawn(ester.scheduler)
    ])


if __name__ == '__main__':
    main()