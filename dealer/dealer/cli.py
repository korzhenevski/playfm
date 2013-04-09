#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import gevent.monkey
gevent.monkey.patch_all()

import logging
from .core import Dealer
from pymongo import Connection


def main():
    connection = Connection(host='192.168.2.2', use_greenlets=True)
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t %(message)s')
    server = Dealer(db=connection['playfm'])
    server.run(workers_addr='tcp://127.0.0.1:10050', workers_results_addr='tcp://127.0.0.1:22005',)


if __name__ == '__main__':
    main()