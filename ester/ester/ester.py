#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import logging
from time import time


class Ester(object):
    def __init__(self, manager, redis, db):
        self.manager = manager
        self.redis = redis
        self.db = db
        self.stat = {}

    def scheduler(self):
        radio_onair = 'radio:onair'

        while True:
            ts = int(time())
            self.stat = {}

            for radio_id in self.redis.zrangebyscore(radio_onair, 0, ts - 120):
                self.manager.delete_radio(radio_id)
                self.redis.zrem(radio_onair, radio_id)
                logging.info('delete radio %s', radio_id)

            for radio_id in self.redis.zrange('radio:now_listen', 0, -1):
                listeners = self.redis.zcard('radio:{}:listeners'.format(radio_id))

                self.stat[radio_id] = listeners

                radio = self.db.radio.find_one({'id': int(radio_id), 'air.track': True, 'deleted_at': 0},
                                               fields=['air.min'])
                if not radio:
                    #logging.debug('radio %s not found', radio_id)
                    continue

                if listeners < radio['air']['min']:
                #logging.debug('radio %s: too few listeners (%s of min %s)', radio_id, listeners, radio['air']['min'])
                    continue

                if self.redis.zadd(radio_onair, radio_id, ts):
                    task = self.manager.put_radio(radio_id)
                    logging.info('schedule radio %s (clients: %s, task_id: %s)', radio_id, listeners, task['_id'])

            gevent.sleep(1)

    def stat_collector(self):
        while True:
            ts = int(time())
            self.db.radio.update({'air.at': {'$lt': ts - 120}}, {'$set': {'air.listeners': 0}})

            for radio_id, listeners in self.stat.iteritems():
                self.db.radio.update({'id': int(radio_id)}, {'$set': {
                    'air.listeners': listeners,
                    'air.at': ts
                }})

            gevent.sleep(10)