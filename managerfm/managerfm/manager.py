#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import time
import ujson as json
from zlib import crc32
import logging

class Manager(object):
    def __init__(self, db, redis):
        self._db = db
        self._redis = redis

    def get_next_id(self, ns):
        ret = self._db.object_ids.find_and_modify({'_id': ns}, {'$inc': {'next': 1}}, new=True, upsert=True)
        return ret['next']

    def track_volume_usage(self, data):
        hostname = data['hostname']
        volume_usage = data['usage']
        update = {'$set': {'usage': volume_usage, 'ts': int(time())}}
        self._db.volume_usage.update({'hostname': hostname}, update, upsert=True)

    def track_onair(self, radio_id, title):
        radio_id = int(radio_id)
        air_id = self._redis.get('radio:{}:air_id'.format(radio_id))

        title = title.strip()
        title_hash = self._fasthash(title)
        previous_title_hash = self._redis.getset('radio:{}:onair_title'.format(radio_id), title_hash)
        if air_id and previous_title_hash == title_hash:
            air = self._redis.hgetall('radio:{}:onair'.format(radio_id))
            self._redis.publish('radio:{}:onair_updates'.format(radio_id), json.dumps(air))
            return air

        air_id = self.get_next_id('air')
        self._redis.set('radio:{}:air_id'.format(radio_id), air_id)

        ts = int(time())
        self._db.air.insert({
            'id': air_id,
            'radio_id': radio_id,
            'ts': ts,
            'title': title,
            'hash': title_hash
        })

        air = {
            'id': air_id,
            'title': title,
            'ts': ts
        }

        self._redis.hmset('radio:{}:onair'.format(radio_id), air)
        self._redis.publish('radio:{}:onair_updates'.format(radio_id), json.dumps(air))

        return air

    def request_task(self, worker_id):
        hostname, wid = worker_id.split(':')
        volumes = self.get_free_volumes(hostname)
        if volumes:
            pass
        logging.debug('task request from %s', worker_id)

    def get_free_volumes(self, hostname, usage_limit=90):
        volume_usage = self._db.volume_usage.find_one({'hostname': hostname})
        if not volume_usage:
            return
        return [vol for vol, usage in volume_usage['usage'].iteritems() if usage['percent'] <= usage_limit]

    def _fasthash(self, data):
        return unicode(crc32(data) & 0xffffffff)
