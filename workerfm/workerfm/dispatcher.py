#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
from gevent.pool import Pool
from gevent.queue import Queue
from .radio import RadioClient
from .writer import StripeWriter

class Dispatcher(object):
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.tasks = {}
        self.results = Queue()

    def dispatch(self, pool_size=None):
        self.pool = Pool(size=pool_size)
        while True:
            self.pool.wait_available()
            task = self.reserve_task()
            if task:
                worker = self.new_worker()
                self.pool.spawn(worker.run, task)
                self.tasks[task['id']] = worker
            gevent.sleep(1)

    def kill_task(self, task_id):
        worker = self.tasks.get(task_id)
        if worker:
            worker.kill()

    def reserve_task(self):
        return self.manager.reserve_for_worker(self.name)

    def new_worker(self):
        return Radio(parent=self)

    def put_result(self, worker, kind, payload=None):
        self.results.put([worker.task['id'], kind, payload])

    def send_results(self):
        for result in self.results:
            print result
            self.manager.save_result(*result)



class Radio(object):
    def __init__(self, parent):
        self.meta = None
        self.parent = parent

    def select_stream(self):
        streams = self.parent.manager.get_streams(self.task['payload']['radio_id'])
        self.stream = streams[0] if streams else None

    def run(self, task):
        self.task = task

        self.select_stream()
        if not self.stream:
            raise RuntimeError('no streams')

        self.radio = RadioClient(self['url'])

        writer_config = task.get('w')
        if writer_config:
            self.writer = StripeWriter(**writer_config)
        else:
            self.writer = None

        self.radio.connect()
        self.parent.handle_start(self)
        self.running = True

        while self.running:
            chunk, meta = self.radio.read()
            if self.writer:
                self.writer.write(chunk)
                self.parent.handle_stripe_write(self)

            if meta and meta != self.meta:
                self.meta = meta
                self.parent.handle_meta(self)

    def kill(self):
        self.running = False
        self.radio.close()
        if self.writer:
            self.writer.close()
