#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gflags
import sys
import logging
from pymongo.mongo_client import MongoClient

FLAGS = gflags.FLAGS
gflags.DEFINE_string('mongo', 'afm', 'MongoDB host')
gflags.DEFINE_string('mongo_db', 'againfm', 'MongoDB name')


def main():
    try:
        FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    db = MongoClient(host=FLAGS.mongo)[FLAGS.mongo_db]

    print db

if __name__ == '__main__':
    main()