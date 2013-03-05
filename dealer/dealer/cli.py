#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import gevent.monkey
gevent.monkey.patch_all()
import logging
from .server import BrokerServer
from redis import Redis

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')
    server = BrokerServer(
        redis=Redis(),
        consumer_addr='tcp://127.0.0.1:22300',
        workers_addr='tcp://127.0.0.1:22302',
        workers_results_addr='tcp://127.0.0.1:22303',
    )
    server.run()

if __name__ == '__main__':
    main()