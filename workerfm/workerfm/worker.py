#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import logging
import socket
import uuid
import os
import psutil
from gevent.pool import Pool
from .radio import RadioClient
from .writer import StripeWriter


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
        self.writer = StripeWriter()

    def run(self, url):
        self.radio = RadioClient(url)

        self.radio.connect()
        self.running = True

        while self.running:
            chunk, meta = self.radio.read()

    def enable_write(self, volume, stripe_size):
        self.writer.configure(volume, stripe_size)

    def disable_write(self):
        self.writer.close()

    def kill(self):
        self.running = False
        self.radio.close()
