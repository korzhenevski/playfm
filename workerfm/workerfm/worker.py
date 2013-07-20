#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent

from gevent.monkey import patch_all

patch_all()

import logging
import socket
from gevent.pool import Pool
from .radio import RadioClient
from .writer import StripeWriter
from time import time
import psutil
import json
import os
from zlib import crc32


def pretty_print(data):
    return json.dumps(data, indent=4)


class Worker(object):
    def __init__(self, manager, server_id):
        self.manager = manager
        if server_id:
            self.server_id = server_id
        else:
            self.server_id = crc32(socket.gethostname()) & 0xffffffff
        self.tasks = {}
        self.stats = psutil.Process(os.getpid())

    def run(self, pool_size):
        self.pool = Pool(size=pool_size)

        while True:
            self.pool.wait_available()
            task = self.reserve_task()
            if task:
                self.run_task(task)
            gevent.sleep(1)

    def reserve_task(self):
        stat = {
            'memory': self.stats.get_memory_percent(),
            'cpu': self.stats.get_cpu_percent(),
            'running': self.pool.size
        }
        return self.manager.task_reserve(self.server_id, stat)

    def run_task(self, task):
        #logging.info('run task: %s', pretty_print(task))

        radio = Radio(task['id'], stream_url=task['stream']['url'])
        radio.manager = self.manager

        self.pool.spawn(radio.run)
        self.tasks[task['id']] = radio

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].stop()
            self.tasks.pop(task_id)


class Radio(object):
    radio_client_class = RadioClient

    def __init__(self, task_id, stream_url):
        self.task_id = task_id
        self.stream_url = stream_url
        self.writer = None
        self.meta = None
        self.manager = None
        self.air_id = -1
        self.last_touch = 0
        self.last_meta = 0

    def run(self):
        self.radio = self.radio_client_class(self.stream_url)
        self.radio.connect()
        self.running = True

        while self.running:
            chunk, meta = self.radio.read()

            if self.track_meta(meta):
                meta_changed, w = self.log_meta()
                if meta_changed:
                    logging.info('meta (air_id %s): %s', self.air_id, self.meta)
                self.writer_control(w)

            if self.writer:
                self.writer.write(chunk)

            self.touch_task()
            gevent.sleep(0)

    def track_meta(self, meta):
        if meta and meta != self.meta:
            self.meta = unicode(meta, 'utf-8', 'ignore').strip()
        elif self.last_meta <= time() - 10:
            self.last_meta = time()
            return True

    def writer_control(self, w):
        if w:
            # create new writer if not exists or volume/name changed
            if not self.writer or (w['volume'] != self.writer.volume or w['name'] != self.writer.name):
                self.writer = StripeWriter(w['volume'], w['name'])
        elif self.writer:
            self.writer.close()
            self.writer = None

    def log_meta(self):
        log = {
            'meta': self.meta,
            'pid': self.air_id,
            'ts': int(time()),
        }

        #logging.info('log meta: %s', pretty_print(log))
        status = self.manager.task_log_meta(self.task_id, log)

        # check air_id change
        pid = self.air_id
        self.air_id = status['air_id']

        return self.air_id != pid, status.get('w')

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
                'name': self.writer.name,
                'volume': self.writer.volume
            }
            #logging.info('task touch: %s', pretty_print(runtime))

        result = self.manager.task_touch(self.task_id, runtime)
        if not result:
            logging.info('stop task')
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

