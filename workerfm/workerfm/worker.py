#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import zerorpc
import zerorpc.exceptions
import os
import psutil
from gevent.pool import Pool
from gevent.queue import Queue
from .radio import RadioClient
from .writer import StripeWriter
import logging
import socket
import uuid


class Worker(object):
    def __init__(self, manager):
        self.manager = manager
        self.name = '{}:{}'.format(socket.gethostname(), uuid.uuid4())
        self.tasks = {}

    def run(self, pool_size):
        self.pool = Pool(size=pool_size)
        while True:
            self.pool.wait_available()
            task = self.request_task()
            if task:
                print task
            gevent.sleep(1)

    def request_task(self):
        logging.debug('request_task')
        self.manager.request_task(self.name)

    def run_task(self, task):
        pass

    def kill_task(self, task_id):
        pass


class VolumeMonitor(object):
    def __init__(self, basepath, manager):
        self.basepath = basepath
        self.manager = manager

    def get_volumes(self):
        volumes = [os.path.join(self.basepath, vol) for vol in os.listdir(self.basepath)]
        volumes = [vol for vol in volumes if os.path.isdir(vol)]
        return volumes

    def get_volume_usage(self, path):
        return dict(psutil.disk_usage(path).__dict__)

    def monitor(self):
        while True:
            volume_usage = dict([(vol, self.get_volume_usage(vol)) for vol in self.get_volumes()])
            print self.manager.track_volume_usage({
                'hostname': socket.gethostname(),
                'usage': volume_usage
            })
            gevent.sleep(10)


class WorkerThread(object):
    def __init__(self, parent):
        self.parent = parent

    def run(self, url):
        self.radio = RadioClient(url)

        self.radio.connect()
        self.running = True

        while self.running:
            chunk, meta = self.radio.read()

    def kill(self):
        self.running = False
        self.radio.close()
