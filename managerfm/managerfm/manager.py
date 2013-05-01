#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ujson as json
from .utils import parse_stream_title, get_ts, fasthash
from pprint import pprint as pp
from datetime import datetime


def from_ts(ts):
    return datetime.fromtimestamp(ts)

# разобратся с "catching up after missing event"
# реконнект при потере связи
# новый страйп - уведомим менеджера
# стата из task_touch - в текущую запись

# http://ester.againfm.dev/record/<radio_id>/<air_id>.mp3
# http://ester.againfm.dev/record/<radio_id><air_id><ip_limit>.mp3
# http://ester.againfm.dev/record/<radio_id>/<start_air_id>-<end_air_id>.mp3

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

    def get_record_url(self, air_id):
        urls = {}
        for stripe in self._db.records.find({'air_id': int(air_id)}):
            name = stripe['name']
            base = 'http://ester.againfm.dev'
            url = '{}/record/{}/{}/{}?start={}'.format(base, name[-1], name[-3:-1], name, stripe['offset'])
            urls[stripe['ts']] = url
        return urls

    def get_radio_record(self, radio_id):
        items = self._db.radio_record.find({'radio_id': int(radio_id)}, fields=['stripe_id', 'ts', 'at', 'air_id'])
        records = []
        for item in items:
            records.append({
                'title': self._db.air.find_one({'id': int(item['air_id'])})['title'],
                'at': from_ts(item['at']).strftime('%Y-%m-%d %H:%M:%S'),
                'ts': from_ts(item['ts']).strftime('%Y-%m-%d %H:%M:%S'),
                'stripe_id': item['stripe_id']
            })
        return records

    def put_radio(self, radio_id):
        task = {
            '_id': self.get_next_id('radio_queue'),
            'radio_id': int(radio_id),
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

        where = {'touch_at': {'$lte': ts - 10}, 'deleted_at': 0, 'radio_id': 917}
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
        task['w'] = {
            'volume': '/tmp/records',
            'stripe_size': 1024 * 1024 * 32,
        }
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

        air = self.track_onair(task['radio_id'], stream_title, prev_id=data['prev_id'])
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


    def track_onair(self, radio_id, title, prev_id=-1):
        radio_id = int(radio_id)
        prev_id = int(prev_id)

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
            'hash': title_hash,
            'prev_id': prev_id
        })

        air = {
            'id': air_id,
            'title': title,
            'ts': ts,
            'prev_id': prev_id
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

