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
            except (requests.RequestException, ValueError):
                logging.exception('cometfm stats request')
                gevent.sleep(5)
                continue

            key = 'radio:scheduled'
            for radio_id, clients in stats.iteritems():
                #if clients <= 5:
                #    continue

                if self.redis.zadd(key, radio_id, time()):
                    task = self.manager.put_radio(radio_id)
                    logging.info('put radio %s (clients: %s, task_id: %s)', radio_id, clients, task['_id'])

            for radio_id in self.redis.zrangebyscore(key, 0, time() - 300):
                self.manager.delete_radio(radio_id)
                self.redis.zrem(key, radio_id)
                logging.info('remove radio %s', radio_id)

            gevent.sleep(1)