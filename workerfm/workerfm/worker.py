#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent

from gevent.monkey import patch_all
patch_all()

import logging
import socket
import uuid
import os
from gevent.pool import Pool
from .radio import RadioClient
from .writer import StripeWriter
from time import time
import psutil
from zlib import crc32

def fasthash(data):
    return crc32(data) & 0xffffffff

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
        thread = Radio(task=task, manager=self.manager)
        self.pool.spawn(thread.run)
        self.tasks[task['id']] = thread

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].stop()
            self.tasks.pop(task_id)


class Radio(object):
    radio_client_class = RadioClient

    def __init__(self, task, manager):
        self.task = task
        self.manager = manager

        self.writer = None
        if 'w' in task:
            self.writer = StripeWriter(task['w']['volume'], task['w']['stripe_size'])

        self.stats = psutil.Process(os.getpid())

    def run(self):
        # привязка меты и дампа к task_id
        # 3 реконнекта на всякий пожарный 1 2 4
        self.radio = self.radio_client_class(self.task['stream']['url'])
        self.radio.connect()

        self.writer.new_stripe()

        self.running = True
        self.meta = None
        self.air_id = None
        self.last_touch = 0

        while self.running:
            chunk, meta = self.radio.read()

            self.update_meta(meta)

            if self.writer:
                self.writer.write(chunk)

            self.touch_task()

    def update_meta(self, meta):
        if not meta.lower().startswith('streamtitle'):
            return

        if self.meta == meta:
            return

        self.meta = meta

        update = {
            'meta': self.meta,
            'ts': int(time()),
            'last_id': self.air_id
        }

        if self.writer:
            update['w'] = self.get_writer_info()

        self.air_id = self.manager.task_update_meta(self.task['id'], update)['air_id']

    def touch_task(self, interval=5):
        if self.last_touch > time() - interval:
            return
        self.last_touch = time()

        update = {
            'air_id': self.air_id,
            'ts': int(time()),
        }
        if self.writer:
            update['w'] = self.get_writer_info()

        status = self.manager.task_touch(self.task['id'], update)
        if status['code'] != 200:
            logging.info('stop %s', status['code'])
            self.stop()

        print ('mem: %s, cpu: %s', self.stats.get_memory_percent(), self.stats.get_cpu_percent())

    def get_writer_info(self):
        return {
            'offset': self.writer.offset,
            'name': self.writer.name
        }

    def stop(self):
        self.running = False
        self.radio.close()

if __name__ == '__main__':
    from pprint import pprint as pp
    from gevent.pool import Pool
    from mock import Mock

    manager = Mock()
    manager.task_touch.return_value = {'code': 200}
    manager.task_update_meta.return_value = {'air_id': 1010}

    def get_task(url):
        task = {
            'id': fasthash(url),
            'stream': {
                'url': url,
                'id': fasthash(url + 'stream')
            },
            'w': {
                'volume': '/tmp/recorder',
                'stripe_size': 1024 * 1024
            }
        }
        return task

    r = Radio(get_task('http://fr2.ah.fm:9000/'), manager)
    r.run()

    print 'exit'

