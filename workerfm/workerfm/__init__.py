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
from gevent.pool import Group
from gevent.wsgi import WSGIServer

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')

FLAGS = gflags.FLAGS

def main():
    try:
        FLAGS(sys.argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

if __name__ == '__main__':
    main()