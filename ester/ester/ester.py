#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import logging
from time import time

requests_log = logging.getLogger('requests')
requests_log.setLevel(logging.WARNING)


class Ester(object):
    def __init__(self, manager, redis):
        self.manager = manager
        self.redis = redis

    def scheduler(self):
        key = 'radio:onair'
        self.redis.delete(key)

        while True:
            ts = int(time())

            for radio_id in self.redis.zrange('radio:now_listen', 0, -1):
                listeners = self.redis.zcard('radio:{}:listeners'.format(radio_id))

                if listeners < 1:
                    continue

                if self.redis.zadd(key, radio_id, ts):
                    task = self.manager.put_radio(radio_id)
                    logging.info('schedule radio %s (clients: %s, task_id: %s)', radio_id, listeners, task['_id'])

            for radio_id in self.redis.zrangebyscore(key, 0, ts - 60):
                self.manager.delete_radio(radio_id)
                self.redis.zrem(key, radio_id)
                logging.info('delete radio %s', radio_id)

            gevent.sleep(1)