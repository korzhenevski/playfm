#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import logging
import socket
import uuid
from gevent.pool import Pool
from .radio import RadioClient
from .writer import StripeWriter


class Worker(object):
    def __init__(self, manager, record_to):
        self.manager = manager
        self.name = '{}:{}'.format(socket.gethostname(), uuid.uuid4())
        self.tasks = {}
        self.record_to = record_to

    def run(self, pool_size):
        self.pool = Pool(size=pool_size)
        while True:
            self.pool.wait_available()
            task = self.request_task()
            if task:
                self.run_task(task)
            gevent.sleep(1)

    def request_task(self):
        logging.debug('request_task')
        return self.manager.request_task(self.name)

    def run_task(self, task):
        thread = WorkerThread(worker=self, manager=self.manager)
        self.pool.spawn(thread.run, task)
        self.tasks[task['_id']] = thread

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].stop()
            self.tasks.pop(task_id)


class WorkerThread(object):
    def __init__(self, worker, manager):
        self.worker = worker
        self.manager = manager

    def run(self, task):
        while True:
            streams = self.manager.get_streams(task['radio_id'])
            if not streams:
                break
            url = streams[0]
            self.loop(url)

    def loop(self, url):
        self.radio = RadioClient(url)

        self.radio.connect()
        self.running = True

        meta = None

        while self.running:
            chunk, current_meta = self.radio.read()

            if meta != current_meta:
                meta = current_meta
                print meta


    def stop(self):
        self.running = False
        self.radio.close()
