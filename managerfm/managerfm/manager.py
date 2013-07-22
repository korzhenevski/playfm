#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from .utils import parse_stream_title, get_ts, fasthash
from datetime import datetime
from functools import wraps
import ujson as json


def from_ts(ts):
    return datetime.fromtimestamp(ts)


def contract(*args, **kwargs):
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *fn_args, **fn_kwargs):
            new_args = [t(raw) for t, raw in zip(args, fn_args)]
            new_kwargs = dict([(k, kwargs[k](v)) for k, v in fn_kwargs.items()])
            return fn(self, *new_args, **new_kwargs)

        return wrapper

    return decorator


class Manager(object):
    def __init__(self, db, redis):
        self._db = db
        self._redis = redis
        self._queue = self._db['stream_queue']

    def put_stream(self, stream_id, do_record=False):
        """ enqueue stream """

        stream_id = int(stream_id)
        do_record = bool(do_record)

        task = self._queue.find_one({'stream_id': stream_id, 'deleted_at': 0})
        if task:
            return task

        task = {
            '_id': self.get_next_id('stream_queue'),
            'stream_id': stream_id,
            'ts': get_ts(),
            'do_record': do_record,
            'deleted_at': 0,
            'retries': 0,
            'touch_at': 0
        }
        self._queue.insert(task)

        return task

    def delete_stream(self, stream_id=None):
        """ delete stream task """
        where = {'deleted_at': 0}
        if stream_id:
            where['stream_id'] = int(stream_id)
        self._queue.update(where, {'$set': {'deleted_at': get_ts()}}, multi=True)
        return where

    def task_reserve(self, server_id, worker_stat=None):
        """ reserve task for worker """
        server_id = int(server_id)
        update = {'$set': {'touch_at': get_ts(), 'server_id': server_id, 'runtime': {}}, '$inc': {'retries': 1}}

        task = self._queue.find_and_modify(
            {'touch_at': {'$lte': get_ts() - 10}, 'retries': {'$lt': 5}, 'deleted_at': 0},
            update, fields=['_id', 'stream_id'], new=True)
        if not task:
            return

        logging.info('worker stat: %s', worker_stat)

        stream = self.select_stream(task['stream_id'])
        if not stream:
            logging.debug('no stream %s', task['stream_id'])
            return

        task['id'] = '{}_{}'.format(server_id, task.pop('_id'))
        task['stream'] = stream

        logging.info('task %s reserved', task['id'])
        return task

    def task_touch(self, task_id, runtime):
        task = self._get_task(task_id)
        if not task:
            return False

        self._queue.update({'_id': task['_id']}, {'$set': {'touch_at': get_ts(), 'runtime': runtime, 'retries': 0}})
        return True

    def task_log_meta(self, task_id, log):
        task = self._get_task(task_id)
        if not task:
            return False

        stream_title = parse_stream_title(log['meta'])
        if not stream_title:
            stream_title = ''

        air = self.track_stream_title(stream_title, stream_id=task['stream_id'], pid=log['pid'])
        air_id = int(air['id'])
        result = {'air_id': air_id}

        if task['do_record']:
            meta_changed = log['pid'] != air_id
            if log['record']:
                self._log_record(task['_id'], task['server_id'], air_id=air_id, record=log['record'])
            result['record'] = self._record_for_task(task, log['record'], air_id=air_id, meta_changed=meta_changed)

        return result

    def _get_task(self, task_id):
        server_id, task_id = map(int, task_id.split('_'))
        return self._queue.find_one({'_id': task_id, 'server_id': server_id, 'deleted_at': 0})

    def _record_for_task(self, task, record_info, air_id, meta_changed):
        name = record_info.get('name')
        if name and (record_info.get('size', 0) >= 1024 * 1024 * 64 or meta_changed):
            self._switch_record(air_id, name)
            name = None

        if not name:
            name = fasthash('{}_{}'.format(task['stream_id'], air_id)) + str(get_ts())[-5:]
            logging.info('new record %s', name)

        return {
            'name': name
        }

    def _switch_record(self, air_id, name):
        record = self._db.records.find_one({'air_id': air_id, 'name': name}, fields=['from', 'to'])
        # TODO: check exception if not record found?
        logging.info('record completed %s', {'air_id': air_id, 'name': name})
        duration = record['to'] - record['from']
        record = self._db.records.find_and_modify({'air_id': air_id, 'name': name},
                                                  {'$set': {'duration': duration, 'status': 1}}, new=True)
        record.pop('_id')
        self._redis.publish('stream:records', json.dumps(record))

    def _log_record(self, task_id, server_id, air_id, record):
        update = {
            '$setOnInsert': {
                'from': record['from'],
                'server_id': server_id,
                'name': record['name'],
                'task_id': task_id,
                'status': 0,
            },
            '$set': {
                'size': record['size'],
                'to': get_ts()
            }
        }
        #logging.debug('log stripe: %s', record)
        self._db.records.update({'air_id': air_id, 'name': record['name']}, update, upsert=True)

    def track_stream_title(self, title, stream_id, pid=-1, ttl=600):
        """ log onair title with duplicate checking """
        stream_id = int(stream_id)
        title = title.strip()
        pid = int(pid)

        # TODO: упростить гавно с хешами
        air_key = 'stream:{}:air_id'.format(stream_id)
        air_id = self._redis.get(air_key)
        self._redis.expire(air_key, ttl)

        title_hash = fasthash(title)
        h_key = 'stream:{}:air_h'.format(stream_id)
        prev_hash = self._redis.getset(h_key, title_hash)
        self._redis.expire(h_key, ttl)

        onair_key = 'stream:{}:onair'.format(stream_id)
        updates_key = 'stream:{}:onair_updates'.format(stream_id)

        if air_id and prev_hash == title_hash:
            air = self._redis.get(onair_key)
            self._redis.expire(onair_key, ttl)

            if air:
                #logging.debug('repeated title')
                self._redis.publish(updates_key, air)
                return json.loads(air)
            else:
                logging.debug('refresh stale onair data')

        air_id = self.get_next_id('air')
        self._redis.set(air_key, air_id)

        ts = get_ts()
        self._db.air.insert({
            'id': air_id,
            'sid': stream_id,
            'ts': ts,
            't': title,
            'h': title_hash,
            'pid': pid,
            'nid': -1
        })

        if pid > 0:
            self._db.air.update({'id': pid}, {'$set': {'nid': air_id}})

        air = {
            'id': air_id,
            't': title,
            'ts': ts,
            'pid': pid
        }
        air_json = json.dumps(air)

        self._redis.set(onair_key, air_json)
        self._redis.expire(onair_key, ttl)
        self._redis.publish(updates_key, air_json)

        logging.debug('new title')
        return air

    def select_stream(self, stream_id):
        """ select exists stream """
        stream = self._db.streams.find_one({'_id': int(stream_id), 'deleted_at': 0}, fields=['url'])
        if stream:
            stream['id'] = stream.pop('_id')
        return stream

    def get_next_id(self, ns):
        ret = self._db.object_ids.find_and_modify({'_id': ns}, {'$inc': {'next': 1}}, new=True, upsert=True)
        return ret['next']
