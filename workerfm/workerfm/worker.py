#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import logging
import socket
import uuid
import os
from gevent.pool import Pool
from .radio import RadioClient
from .writer import StripeWriter
from time import time
import psutil


class Worker(object):
    def __init__(self, manager, record_to):
        self.manager = manager
        self.name = '{}:{}'.format(socket.gethostname(), uuid.uuid4())
        self.tasks = {}
        self.record_to = record_to
        self.stats = psutil.Process(os.getpid())

    def run(self, pool_size):
        self.pool = Pool(size=pool_size)
        while True:
            self.pool.wait_available()
            #logging.debug('mem: %s, cpu: %s', self.stats.get_memory_percent(), self.stats.get_cpu_percent())
            task = self.reserve_task()
            if task:
                self.run_task(task)
            gevent.sleep(1)

    def reserve_task(self):
        #logging.debug('reserve_task')
        return self.manager.task_reserve(self.name)

    def run_task(self, task):
        thread = WorkerThread(task=task, manager=self.manager)
        self.pool.spawn(thread.run)
        self.tasks[task['id']] = thread

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].stop()
            self.tasks.pop(task_id)


class WorkerThread(object):
    def __init__(self, task, manager):
        self.task = task
        self.manager = manager
        self.writer = StripeWriter()
        self.writer.configure(volume='/tmp/record')

    def run(self):
        self.radio = RadioClient(self.task['stream']['url'])
        self.radio.connect()

        self.running = True
        self.meta = None
        self.air_id = None
        self.last_touch = 0

        while self.running:
            chunk, meta = self.radio.read()

            if self.air_id:
                self.write_stripe(chunk)

            self.update_meta(meta)

            if self.touch_task() == 404:
                self.stop()
                logging.warning('task gone')

    def update_meta(self, meta):
        if not meta.lower().startswith('streamtitle'):
            return

        if self.meta == meta:
            return

        self.meta = meta
        air_id = self.manager.task_update_meta(self.task['id'], self.meta)
        if air_id:
            self.writer.new_stripe()
            self.air_id = air_id

    def write_stripe(self, chunk):
        self.writer.write(chunk)
        self.manager.task_stripe_commit(self.task['id'], {
            'air_id': self.air_id,
            'offset': self.writer.offset,
            'stripe': self.writer.name,
            'radio_id': self.task['radio_id'],
            'stream_id': self.task['stream']['id'],
        })

    def touch_task(self):
        ts = time()
        if self.last_touch >= ts - 5:
            return
        #logging.debug('touch_task')
        self.last_touch = ts
        return self.manager.task_touch(self.task['id'])

    def stop(self):
        self.running = False
        self.radio.close()
