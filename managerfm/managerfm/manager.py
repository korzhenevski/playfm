#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ujson as json
from .utils import parse_stream_title, get_ts, fasthash
from pprint import pprint as pp
from datetime import datetime


def from_ts(ts):
    return datetime.fromtimestamp(ts)

class Manager(object):
    def __init__(self, db, redis):
        self._db = db
        self._redis = redis
        self._rq = self._db.radio_queue

    def get_next_id(self, ns):
        ret = self._db.object_ids.find_and_modify({'_id': ns}, {'$inc': {'next': 1}}, new=True, upsert=True)
        return ret['next']

    def select_stream(self, radio_id):
        """ select best online stream """
        where = {'radio_id': int(radio_id), 'deleted_at': 0, 'is_online': True}
        return self._db.streams.find_one(where, fields={'_id': 0, 'id': 1, 'url': 1, 'bitrate': 1},
                                         sort=[('bitrate', -1)])

    def put_radio(self, radio_id):
        radio_id = int(radio_id)

        task = self._rq.find_one({'radio_id': radio_id, 'deleted_at': 0})
        if task:
            return task

        task = {
            '_id': self.get_next_id('radio_queue'),
            'radio_id': radio_id,
            'touch_at': 0,
            'deleted_at': 0
        }
        self._rq.insert(task)
        return task

    def delete_radio(self, radio_id=None):
        where = {'deleted_at': 0}
        if radio_id:
            where['radio_id'] = int(radio_id)
        self._rq.update(where, {'$set': {'deleted_at': get_ts()}})

    def task_reserve(self, worker_id):
        """ reserve task for worker """
        ts = get_ts()

        where = {'touch_at': {'$lte': ts - 10}, 'deleted_at': 0}
        update = {'touch_at': ts, 'worker': worker_id}
        task = self._rq.find_and_modify(where, {'$set': update}, fields=['_id', 'radio_id'], new=True)

        if not task:
            return

        stream = self.select_stream(task['radio_id'])
        if not stream:
            logging.debug('no stream for radio %s', task['radio_id'])
            return

        task['id'] = task.pop('_id')
        task['stream'] = stream

        # Stripe params
        #task['w'] = {
        #    'volume': '/tmp/records',
        #    'stripe_size': 1024 * 1024 * 32,
        #}
        logging.info('task %s reserved to worker %s', task['id'], worker_id)

        return task

    def task_touch(self, task_id, runtime):
        task = self._rq.find_one({'_id': int(task_id), 'deleted_at': 0}, fields=['radio_id'])
        if not task:
            return {'code': 404}

        self._rq.update({'_id': int(task_id)}, {'$set': {'touch_at': get_ts(), 'runtime': runtime}})
        return {'code': 200}

    def task_log_meta(self, task_id, data):
        task_id = int(task_id)

        task = self._rq.find_one({'_id': task_id, 'deleted_at': 0}, fields=['radio_id'])
        if not task:
            logging.debug('no task')
            return

        stream_title = parse_stream_title(data['meta'])
        if not stream_title:
            stream_title = ''

        air = self.track_onair(task['radio_id'], stream_title, pid=data['pid'])
        air_id = int(air['id'])

        return {'air_id': air_id}

    def task_log_stripe(self, task_id, update):
        logging.info('stripe update (task %s): %s', task_id, update)
        record = {
            '$set': {
                'task_id': int(task_id),
                'offset': int(update['offset']),
                'ts': get_ts()
            }
        }
        self._db.records.update({'air_id': int(update['air_id']), 'name': update['name']}, record, upsert=True)

    def track_onair(self, radio_id, title, pid=-1, ttl=120):
        """
        log onair title with duplicate checking
        """
        radio_id = int(radio_id)
        title = title.strip()
        pid = int(pid)

        air_key = 'radio:{}:air_id'.format(radio_id)
        air_id = self._redis.get(air_key)
        self._redis.expire(air_key, ttl)

        title_hash = fasthash(title)
        h_key = 'radio:{}:air_h'.format(radio_id)
        prev_hash = self._redis.getset(h_key, title_hash)
        self._redis.expire(h_key, ttl)

        onair_key = 'radio:{}:onair'.format(radio_id)
        updates_key = 'radio:{}:onair_updates'.format(radio_id)

        print air_id, prev_hash

        if air_id and prev_hash == title_hash:
            air = self._redis.get(onair_key)
            self._redis.expire(onair_key, ttl)

            if air:
                logging.debug('repeated title')
                self._redis.publish(updates_key, air)
                return json.loads(air)
            else:
                logging.debug('refresh stale onair data')

        air_id = self.get_next_id('air')
        self._redis.set(air_key, air_id)

        ts = get_ts()
        self._db.air.insert({
            'id': air_id,
            'radio_id': radio_id,
            'ts': ts,
            'title': title,
            'h': title_hash,
            'pid': pid,
            'nid': -1
        })
        if pid > 0:
            self._db.air.update({'id': pid}, {'$set': {'nid': get_ts()}})

        air = {
            'id': air_id,
            'title': title,
            'ts': ts,
            'pid': pid
        }
        air_json = json.dumps(air)

        self._redis.set(onair_key, air_json)
        self._redis.publish(updates_key, air_json)

        logging.debug('new title')
        return air

    def get_air(self, radio_id, limit=10):
        radio_id = int(radio_id)
        history = self._db.air.find({'radio_id': int(radio_id)}, fields={'_id': 0}).sort('ts', 1).limit(limit)
        return list(history)

    def get_free_volumes(self, hostname, usage_limit=90):
        volume_usage = self._db.volume_usage.find_one({'hostname': hostname})
        if not volume_usage:
            return
        return [vol for vol, usage in volume_usage['usage'].iteritems() if usage['percent'] <= usage_limit]

