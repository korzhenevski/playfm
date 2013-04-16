#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent.monkey import patch_all
patch_all()

import gevent
import zerorpc
from .dispatcher import Dispatcher
from pprint import pprint as pp

def main():
    manager = zerorpc.Client('tcp://localhost:4242')
    dispatcher = Dispatcher('test_worker', manager)
    gevent.joinall([
        gevent.spawn(dispatcher.dispatch, pool_size=1),
        gevent.spawn(dispatcher.send_results)
    ])

if __name__ == '__main__':
    main()


def test():
    """
    writer = StripeWriter(base='/tmp/records', prefix='ah', rotate_size=1024 * 1024)
    for i in xrange(4):
        writer.write('a' * 1024 * 1024)
        print writer.name
        print writer.path
    writer.close()
    """

    from .radio import RadioClient
    client = RadioClient('http://fr2.ah.fm:9000/;', timeout=1)
    client = RadioClient('http://nsk-ru.l.nullwave.fm:8000/russian_pop', timeout=5)
    client.connect()
    pp(client.headers)
    while True:
        data = client.read()
        print len(data[0]), data[1]

    #for meta in client.stream_meta():
    #    print meta