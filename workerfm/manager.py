#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zerorpc
from pymongo.mongo_client import MongoClient
from time import time

class Manager(object):
    def __init__(self, db):
        self._db = db

    def get_streams(self, radio_id):
        where = {'radio_id': int(radio_id), 'deleted_at': 0, 'is_online': True}
        return list(self._db.streams.find(where, fields={'_id': 0, 'url': 1, 'id': 1, 'bitrate': 1}))

    def reserve_task(self, worker_id):
        ts = int(time())
        where = {'status': {'$in': ['pending', 'processing']}, 'heartbeat_at': {'$lte': ts - 10}}
        return self._db.tasks.find_and_modify(where, {'$set': {
            'worker_id': worker_id,
            'status': 'processing',
            'heartbeat_at': ts,
        }}, fields={'_id': 0, 'id': 1, 'payload': 1, 'name': 1})

    def record_radio(self, radio_id):
        return self.put_task('record_radio', {'radio_id': radio_id})

    def put_task(self, name, payload):
        task_id = self.get_next_id('tasks')
        self._db.tasks.insert({
            'id': task_id,
            'name': name,
            'payload': payload,
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

db = MongoClient(host='192.168.2.2')['againfm']
manager = Manager(db)

server = zerorpc.Server(manager)
server.bind('tcp://*:4242')
server.run()
