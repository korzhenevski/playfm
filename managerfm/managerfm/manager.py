#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ujson as json
from .utils import parse_stream_title, get_ts, fasthash

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
                                         sort=[('bitrate', 1)])

    def put_radio(self, radio_id):
        task = {
            '_id': self.get_next_id('radio_queue'),
            'radio_id': int(radio_id),
            'touch_at': 0,
            'deleted_at': 0
        }
        self._rq.insert(task)
        return task

    def delete_radio(self, radio_id):
        self._rq.update({'radio_id': int(radio_id), 'deleted_at': 0}, {'$set': {'deleted_at': get_ts()}})

    def reserve_task(self, worker_id):
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
        logging.info('task %s reserved to worker %s', task['id'], worker_id)

        return task

    def touch_task(self, task_id):
        task = self._rq.find_one({'_id': int(task_id), 'deleted_at': 0}, fields=['radio_id'])
        if not task:
            return 404

        self._rq.update({'_id': int(task_id)}, {'$set': {'touch_at': get_ts()}})
        return True

    def update_task_meta(self, task_id, meta):
        task = self._rq.find_one({'_id': int(task_id), 'deleted_at': 0}, fields=['radio_id'])
        if not task:
            logging.debug('no task')
            return

        stream_title = parse_stream_title(meta)
        if not stream_title:
            logging.debug('invalid meta')
            return

        air = self.track_onair(task['radio_id'], stream_title)
        print air
        return air['id']

    def track_onair(self, radio_id, title):
        radio_id = int(radio_id)
        air_id = self._redis.get('radio:{}:air_id'.format(radio_id))

        title = title.strip()
        title_hash = fasthash(title)
        previous_title_hash = self._redis.getset('radio:{}:onair_title'.format(radio_id), title_hash)
        if air_id and previous_title_hash == title_hash:
            logging.debug('repeated title')
            air = self._redis.hgetall('radio:{}:onair'.format(radio_id))
            self._redis.publish('radio:{}:onair_updates'.format(radio_id), json.dumps(air))
            return air

        air_id = self.get_next_id('air')
        self._redis.set('radio:{}:air_id'.format(radio_id), air_id)

        ts = get_ts()
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

        logging.debug('new title')

        return air

    def get_free_volumes(self, hostname, usage_limit=90):
        volume_usage = self._db.volume_usage.find_one({'hostname': hostname})
        if not volume_usage:
            return
        return [vol for vol, usage in volume_usage['usage'].iteritems() if usage['percent'] <= usage_limit]

