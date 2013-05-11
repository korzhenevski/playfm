#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import requests
import logging
from time import time
from gevent.queue import Queue

requests_log = logging.getLogger('requests')
requests_log.setLevel(logging.WARNING)


class Ester(object):
    def __init__(self, manager, redis):
        self.manager = manager
        self.redis = redis

    def scheduler(self):
        while True:
            try:
                resp = requests.get('http://127.0.0.1:6000/stats?clients=1')
                stats = resp.json()['stats']
            except Exception, exc:
                logging.exception('cometfm stats request')
                gevent.sleep(5)
                continue

            name = 'radio:scheduled'
            for radio_id, clients in stats.iteritems():
                if clients <= 3:
                    continue
                if self.redis.zadd(name, radio_id, time()):
                    task = self.manager.put_radio(radio_id)
                    logging.info('put radio %s (clients: %s, task_id: %s)', radio_id, clients, task['_id'])

            for radio_id in self.redis.zrangebyscore(name, 0, time() - 10):
                self.manager.delete_radio(radio_id)
                self.redis.zrem(name, radio_id)
                logging.info('remove radio %s', radio_id)

            gevent.sleep(1)