#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import ujson as json
from .utils import parse_stream_title, get_ts, fasthash
from datetime import datetime


def from_ts(ts):
    return datetime.fromtimestamp(ts)


class Manager(object):
    def __init__(self, db, redis):
        self._db = db
        self._redis = redis
        self._queue = self._db['stream_queue']

    def select_stream(self, stream_id):
        """ select exists stream """
        stream = self._db.streams.find_one({'_id': int(stream_id), 'deleted_at': 0}, fields=['url'])
        if stream:
            stream['id'] = stream.pop('_id')
        return stream

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
            'ts': 0,
            'do_record': do_record,
            'deleted_at': 0,
            'touch_at': 0
        }
        self._queue.insert(task)

        return task

    def delete_stream(self, stream_id=None):
        """ delete stream task """
        where = {'deleted_at': 0}
        if stream_id:
            where['stream_id'] = int(stream_id)
        self._queue.update(where, {'$set': {'deleted_at': get_ts()}})

    def task_reserve(self, server_id, worker_stat=None):
        """ reserve task for worker """
        update = {'$set': {'touch_at': get_ts(), 'server_id': int(server_id), 'runtime': {}}}
        task = self._queue.find_and_modify({'touch_at': {'$lte': get_ts() - 10}, 'deleted_at': 0},
                                           update, fields=['_id', 'stream_id'], new=True)
        if not task:
            return

        logging.info('worker stat: %s', worker_stat)

        stream = self.select_stream(task['stream_id'])
        if not stream:
            logging.debug('no stream %s', task['stream_id'])
            return

        task['id'] = task.pop('_id')
        task['stream'] = stream

        logging.info('task %s reserved to server %s', task['id'], server_id)
        return task

    def task_touch(self, task_id, runtime):
        task_id = int(task_id)

        task = self._queue.find_one({'_id': task_id, 'deleted_at': 0})
        if not task:
            return False

        if 'w' in runtime:
            self._log_record(task_id, server_id=task['server_id'], air_id=runtime['air_id'], record=runtime['w'])

        self._queue.update({'_id': task_id}, {'$set': {'touch_at': get_ts(), 'runtime': runtime}})
        return True

    def _log_record(self, task_id, server_id, air_id, record):
        update = {
            '$setOnInsert': {
                'ts': get_ts(),
                'server_id': int(server_id),
                'volume': record['volume'],
                'name': record['name'],
                'task_id': task_id,
                'status': 0,
            },
            '$set': {
                'offset': int(record['offset']),
                'at': get_ts()
            }
        }
        logging.debug('log stripe: %s', record)

        self._db.records.update({'air_id': air_id, 'name': record['name']}, update, upsert=True)

    def task_log_meta(self, task_id, log):
        task_id = int(task_id)

        task = self._queue.find_one({'_id': task_id, 'deleted_at': 0},
                                    fields=['stream_id', 'do_record', 'runtime.w'])
        if not task:
            logging.debug('no task %s', task_id)
            return

        stream_title = parse_stream_title(log['meta'])
        if not stream_title:
            stream_title = ''

        air = self.track_onair(task['stream_id'], stream_title, pid=log['pid'])
        result = {'air_id': int(air['id'])}

        if task['do_record']:
            result['w'] = self._record_for_task(task, air_id=air['id'])

        return result

    def _get_record_id(self, stream_id, air_id):
        return fasthash('{}_{}'.format(stream_id, air_id)) + str(get_ts())[-5:]

    def _record_for_task(self, task, air_id):
        w = task['runtime'].get('w', {})
        name = w.get('name')
        need_rotate = w.get('offset', 0) >= 1024 * 1024 * 0.2

        if not name or need_rotate:
            if need_rotate:
                record = self._db.records.find_one({'air_id': air_id, 'name': name}, fields=['at', 'ts'])
                # TODO: check exception if noy record found? 
                logging.info('need rotate air_id: %s, name: %s record: %s', air_id, name, record)
                duration = record['at'] - record['ts']
                self._db.records.update({'air_id': air_id, 'name': name}, {'$set': {'duration': duration, 'status': 1}})

            name = fasthash('{}_{}'.format(task['stream_id'], air_id)) + str(get_ts())[-5:]

        return {
            'volume': '/tmp/worker_records',
            'name': name
        }

    def track_onair(self, stream_id, title, pid=-1, ttl=600):
        """ log onair title with duplicate checking """
        stream_id = int(stream_id)
        title = title.strip()
        pid = int(pid)

        # TODO: упростить гавно с хешами
        air_key = 'radio:{}:air_id'.format(stream_id)
        air_id = self._redis.get(air_key)
        self._redis.expire(air_key, ttl)

        title_hash = fasthash(title)
        h_key = 'radio:{}:air_h'.format(stream_id)
        prev_hash = self._redis.getset(h_key, title_hash)
        self._redis.expire(h_key, ttl)

        onair_key = 'radio:{}:onair'.format(stream_id)
        updates_key = 'radio:{}:onair_updates'.format(stream_id)

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
            'stream_id': stream_id,
            'ts': ts,
            'title': title,
            'h': title_hash,
            'pid': pid,
            'nid': -1
        })

        if pid > 0:
            self._db.air.update({'id': pid}, {'$set': {'nid': air_id}})

        air = {
            'id': air_id,
            'title': title,
            'ts': ts,
            'pid': pid
        }
        air_json = json.dumps(air)

        self._redis.set(onair_key, air_json)
        self._redis.expire(onair_key, ttl)
        self._redis.publish(updates_key, air_json)

        logging.debug('new title')
        return air

    def get_next_id(self, ns):
        ret = self._db.object_ids.find_and_modify({'_id': ns}, {'$inc': {'next': 1}}, new=True, upsert=True)
        return ret['next']
