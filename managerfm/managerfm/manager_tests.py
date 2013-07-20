#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import pymongo
import redis
from managerfm.manager import Manager
from managerfm.utils import get_ts


class ManagerTest(unittest.TestCase):
    TEST_DB = 'manager_tests'

    def setUp(self):
        self.mongo = pymongo.Connection()
        self.db = self.mongo[self.TEST_DB]
        self.redis = redis.Redis(db=6)
        self.manager = Manager(self.db, self.redis)

    def testPutStream(self):
        stream_id = 10

        task = self.manager.put_stream(stream_id)
        self.assertEqual(stream_id, task['stream_id'])

        exists_task = self.manager.put_stream(stream_id)
        self.assertEqual(task['_id'], exists_task['_id'])

    def testSelectStream(self):
        exists_stream = {'_id': 10, 'url': 'http://www.example.com/stream1', 'deleted_at': 0}
        self.db.streams.insert(exists_stream)

        deleted_stream = {'_id': 11, 'url': 'http://www.example.com/stream2', 'deleted_at': get_ts()}
        self.db.streams.insert(deleted_stream)

        self.assertDictEqual(self.manager.select_stream(10), {'id': 10, 'url': 'http://www.example.com/stream1'})
        self.assertIsNone(self.manager.select_stream(11))

    def tearDown(self):
        self.redis.flushdb()
        self.mongo.drop_database(self.TEST_DB)
