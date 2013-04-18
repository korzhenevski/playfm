#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import time
import ujson as json
from zlib import crc32


def fasthash(data):
    return crc32(data) & 0xffffffff


class Manager(object):
    def __init__(self, db, redis):
        self._db = db
        self._redis = redis

    def get_streams(self, radio_id):
        """ get online streams """
        where = {'radio_id': int(radio_id), 'deleted_at': 0, 'is_online': True}
        return list(self._db.streams.find(where, fields={'_id': 0, 'id': 1, 'url': 1, 'bitrate': 1}))

    def reserve_for_worker(self, worker_id):
        ts = int(time())
        where = {'status': {'$in': ['pending', 'processing']}, 'heartbeat_at': {'$lte': ts - 10}}
        data = self._db.tasks.find_and_modify(where, {'$set': {
            'worker_id': worker_id,
            'status': 'processing',
            'heartbeat_at': ts,
            }}, fields={'_id': 0, 'id': 1, 'radio_id': 1, 'record': True})
        if not data:
            return
        task = {'id': data['id']}
        task.update(data['request'])
        return task

    def record_radio(self, radio_id):
        self.track_radio(radio_id, record=True)

    def track_radio(self, radio_id, record=False):
        # mark deleted exists task
        self._db.tasks.update({'id': int(radio_id)}, {'$set': {'status': 'deleted', 'deleted_at': int(time())}})
        # create new task
        task_id = self.get_next_id('tasks')
        self._db.tasks.insert({
            'id': task_id,
            'radio_id': radio_id,
            'record': record,
            'status': 'pending',
            'heartbeat_at': 0,
            'created_at': int(time())
        })
        return {'task_id': task_id}

    def drop_task(self, task_id):
        self._db.tasks.update({'id': int(task_id)}, {'$set': {'status': 'deleted'}})

    def get_next_id(self, ns):
        ret = self._db.object_ids.find_and_modify({'_id': ns}, {'$inc': {'next': 1}}, new=True, upsert=True)
        return ret['next']

    def save_result(self, task_id, name, data):
        task_id = int(task_id)
        result_field = 'result.' + name
        self._db.tasks.update({'task_id': task_id}, {'$set': {'heartbeat_at': 0, result_field: data}})
        print task_id, name, data

    def onair(self, radio_id, title):
        radio_id = int(radio_id)
        title = unicode(title).strip()
        title_hash = unicode(fasthash(title))
        cache_key = 'radio:{}:onair_title'.format(radio_id)

        air_id = self._redis.get('radio:{}:air_id'.format(radio_id))

        if air_id and self._redis.getset(cache_key, title_hash) == title_hash:
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
