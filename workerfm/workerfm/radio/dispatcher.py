#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
from gevent.pool import Pool
from .radio import RadioClient
from .writer import StripeWriter


class Dispatcher(object):
    def __init__(self, pool_size=None):
        self.pool = Pool(size=pool_size)

    def dispatch(self):
        while True:
            self.pool.wait_available()

    def new_worker(self):
        return Worker(parent=self)

    def handle_meta(self, worker):
        print worker.meta

    def handle_stripe_write(self, worker):
        print worker.writer.path, worker.writer.written

    def handle_start(self, worker):
        print worker.radio.headers

    def handle_worker(self, worker):
        pass

class Worker(object):
    def __init__(self, parent):
        self.parent = parent
        self.meta = None

    def run(self, task):
        self.task = task
        self.radio = RadioClient(task['url'])

        writer_config = task.get('w')
        if writer_config:
            self.writer = StripeWriter(**writer_config)
        else:
            self.writer = None

        self.radio.connect()
        self.running = True

        while self.running:
            chunk, meta = self.radio.read()
            if self.writer:
                self.writer.write(chunk)

            if meta != self.meta:
                self.meta = meta

            self.parent.handle_worker(self)

        self.radio.close()

    def kill(self):
        self.running = False
        self.radio.close()
        if self.writer:
            self.writer.close()
