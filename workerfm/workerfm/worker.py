#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent

from gevent.monkey import patch_all

patch_all()

import logging
import socket
from gevent.pool import Pool
from .radio import RadioClient
from .recorder import Recorder
from time import time
import psutil
import json
import os
from zlib import crc32


def pretty_print(data):
    return json.dumps(data, indent=4)


class Worker(object):
    def __init__(self, manager, server_id, record_to):
        self.manager = manager

        if server_id:
            self.server_id = server_id
        else:
            self.server_id = crc32(socket.gethostname()) & 0xffffffff >> 2
        self.server_id = int(self.server_id)

        self.tasks = {}
        self.stats = psutil.Process(os.getpid())
        self.record_to = record_to

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

        radio = Radio(task['id'], stream_url=task['stream']['url'], record_to=self.record_to)
        radio.manager = self.manager

        self.pool.spawn(radio.run)
        self.tasks[task['id']] = radio

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].stop()
            self.tasks.pop(task_id)


class Radio(object):
    radio_client_class = RadioClient

    def __init__(self, task_id, stream_url, record_to):
        self.task_id = task_id
        self.stream_url = stream_url
        self.record_to = record_to
        self.recorder = None
        self.meta = None
        self.manager = None
        self.air_id = -1
        self.last_touch = 0
        self.last_meta = 0
        self.network_traffic = 0
        self.record_from = 0

    def run(self):
        self.radio = self.radio_client_class(self.stream_url)
        self.radio.connect()
        self.running = True

        while self.running:
            chunk, meta = self.radio.read()
            self.network_traffic += len(chunk)
            if meta:
                self.network_traffic += len(meta)

            if self.track_meta(meta):
                meta_changed, record = self.log_meta()
                if meta_changed:
                    logging.info('meta (air_id %s): %s', self.air_id, self.meta)
                self.setup_recorder(record)

            if self.recorder:
                self.recorder.write(chunk)

            self.touch_task()
            gevent.sleep(0)

    def track_meta(self, meta):
        if meta and meta != self.meta:
            self.meta = unicode(meta, 'utf-8', 'ignore').strip()
        else:
            return True

    def setup_recorder(self, record_info):
        if record_info:
            # create new recorder if not exists or name changed
            if not self.recorder or record_info['name'] != self.recorder.name:
                self.recorder = Recorder(self.record_to)
                self.recorder.open(record_info['name'])
                logging.info('task %s new stripe %s', self.task_id, self.recorder.path)
                self.record_from = int(time())
        elif self.recorder:
            self.recorder.close()
            self.recorder = None

    def log_meta(self):
        log = {
            'meta': self.meta,
            'pid': self.air_id,
            'ts': int(time()),
            'record': {}
        }

        if self.recorder:
            log['record'] = self.get_record_info()

        #logging.info('log meta: %s', pretty_print(log))
        status = self.manager.task_log_meta(self.task_id, log)
        if not status:
            logging.info('stop task')
            self.stop()

        # check air_id change
        pid = self.air_id
        self.air_id = status['air_id']

        return self.air_id != pid, status.get('record')

    def touch_task(self, interval=1):
        # throttle calls
        if self.last_touch > time() - interval:
            return
        self.last_touch = time()

        runtime = {
            'air_id': self.air_id,
            'network_traffic': self.network_traffic
        }

        if self.recorder:
            runtime['record'] = self.get_record_info()

        result = self.manager.task_touch(self.task_id, runtime)
        if not result:
            logging.info('stop task')
            self.stop()

    def get_record_info(self):
        return {
            'from': self.record_from,
            'size': self.recorder.size,
            'name': self.recorder.name,
        }

    def stop(self):
        self.running = False
        self.radio.close()
