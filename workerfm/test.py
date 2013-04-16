#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zerorpc
from time import time
client = zerorpc.Client('tcp://localhost:4242')

for x in xrange(1000):
    ts = time()
    client.get_stream(1000)
    print time() - ts