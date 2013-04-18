#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zerorpc
import gflags
import sys
import logging
from pymongo.mongo_client import MongoClient
from redis import Redis

from .manager import Manager

FLAGS = gflags.FLAGS
gflags.DEFINE_string('redis', '127.0.0.1', 'Redis host')
gflags.DEFINE_integer('redis_db', 0, 'Redis database')
gflags.DEFINE_string('mongo', '127.0.0.1', 'MongoDB host')
gflags.DEFINE_string('mongo_db', 'againfm', 'MongoDB name')
gflags.DEFINE_string('bind', 'tcp://*:4242', 'Server ZMQ bind')


def main():
    try:
        FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')

    db = MongoClient(host=FLAGS.mongo)[FLAGS.mongo_db]
    redis = Redis(host=FLAGS.redis, db=FLAGS.redis_db)
    manager = Manager(db, redis)

    server = zerorpc.Server(manager)
    server.bind(FLAGS.bind)
    logging.info('server bind on %s', FLAGS.bind)
    server.run()

if __name__ == '__main__':
    main()