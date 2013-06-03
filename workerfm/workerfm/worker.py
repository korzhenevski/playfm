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


class Worker(object):
    def __init__(self, manager, record_to):
        self.manager = manager
        self.name = '{}:{}'.format(socket.gethostname(), uuid.uuid4())
        self.tasks = {}
        self.record_to = record_to
        self.stats = psutil.Process(os.getpid())

    def run(self, pool_size):
        self.pool = Pool(size=pool_size)
        logging.info('start worker pool: %s', pool_size)
        while True:
            self.pool.wait_available()
            #logging.debug('mem: %s, cpu: %s', self.stats.get_memory_percent(), self.stats.get_cpu_percent())
            task = self.reserve_task()
            if task:
                self.run_task(task)
            gevent.sleep(1)

    def reserve_task(self):
        return self.manager.task_reserve(self.name)

    def run_task(self, task):
        logging.info('run task: %s', task)
        radio = Radio(task['id'], stream_url=task['stream']['url'], writer=task.get('w'))
        radio.manager = self.manager
        self.pool.spawn(radio.run)
        self.tasks[task['id']] = radio

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].stop()
            self.tasks.pop(task_id)


class Radio(object):
    radio_client_class = RadioClient

    def __init__(self, task_id, stream_url, writer=None):
        self.task_id = task_id
        self.stream_url = stream_url

        self.writer = None
        if writer:
            self.writer = StripeWriter(writer['volume'], writer['stripe_size'])

        self.meta = None
        self.manager = None
        self.air_id = -1
        self.last_touch = 0

    def run(self):
        self.radio = self.radio_client_class(self.stream_url)
        self.radio.connect()
        self.running = True

        while self.running:
            chunk, meta = self.radio.read()
            meta_changed = self.log_meta(meta)

            if meta_changed:
                logging.info('meta (air_id %s): %s', self.air_id, self.meta)

            if self.writer:
                if meta_changed or self.writer.need_rotate():
                    self.new_stripe()
                self.writer.write(chunk)

            self.touch_task()
            gevent.sleep(0)

    def new_stripe(self):
        self.writer.new_stripe()
        self.manager.task_log_stripe(self.task_id, {
            'air_id': self.air_id,
            'offset': 0,
            'name': self.writer.name,
        })

    def log_meta(self, meta):
        meta = unicode(meta or '')

        if not meta.lower().startswith('streamtitle'):
            return

        if self.meta == meta:
            return

        self.meta = meta
        update = {
            'meta': self.meta,
            'ts': int(time()),
            'pid': self.air_id
        }

        logging.info('update meta: %s', update)
        status = self.manager.task_log_meta(self.task_id, update)

        # check air_id change
        pid = self.air_id
        self.air_id = status['air_id']

        return self.air_id != pid

    def touch_task(self, interval=5):
        # throttle calls
        if self.last_touch > time() - interval:
            return
        self.last_touch = time()

        runtime = {
            'air_id': self.air_id,
            'ts': int(time()),
        }
        if self.writer:
            runtime['w'] = {
                'offset': self.writer.offset,
                'name': self.writer.name
            }
        #logging.info('task touch: %s', runtime)

        status = self.manager.task_touch(self.task_id, runtime)
        if status['code'] != 200:
            logging.info('stop %s', status['code'])
            self.stop()

    def stop(self):
        self.running = False
        self.radio.close()


if __name__ == '__main__':
    from pprint import pprint as pp
    from zlib import crc32

    def fasthash(data):
        return crc32(data) & 0xffffffff

    class Manager(object):
        def task_touch(self, task_id, runtime):
            pp([task_id, runtime])
            return {'code': 200}

        def task_log_meta(self, task_id, update):
            pp([task_id, update])
            return {'air_id': 1010}

    def get_task(url):
        task = {
            'task_id': fasthash(url),
            'stream_url': url,
            #'writer': {
            #    'volume': '/tmp/recorder',
            #    'stripe_size': 1024 * 1024
            #}
        }
        return task

    r = Radio(**get_task('http://fr2.ah.fm:9000/'))
    r.manager = Manager()
    r.run()

    print 'exit'

