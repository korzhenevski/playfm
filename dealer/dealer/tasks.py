#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from collections import deque, defaultdict
from durabledict import RedisDict
from spike_pb2 import Task, Request

class TasksDict(RedisDict):
    def _encode(self, task):
        return task.SerializeToString()

    def _decode(self, task):
        # add exceptions
        return Task.FromString(task)

    def durables(self):
        encoded = self.conn.hgetall(self.keyspace)
        tuples = [(int(k), self._decode(v)) for k, v in encoded.items()]
        return dict(tuples)

class Tasks:
    """Currently executing tasks."""
    def __init__(self, redis):
        self.redis = redis
        self.tasks = TasksDict('broker:tasks', connection=self.redis)
        self.waiting = deque()
        self.processing = deque()
        self.workers_tasks = defaultdict(set)
        self.task_on_worker = {}

    def put_task(self, task):
        if task.id in self.tasks:
            return
        self.tasks[task.id] = task
        self.waiting.append(task.id)
        self.redis.lpush('spiker:waiting', task.id)
        return True

    def remove_task(self, task_id):
        if task_id not in self.tasks:
            return
        del self.tasks[task_id]
        self.remove_worker_task(task_id)
        return True

    def get_task(self, worker_id=None):
        if not self.waiting:
            return
        task_id = self.waiting.pop()
        self.redis.lrem('spiker:waiting', task_id)
        if task_id not in self.tasks:
            return
        self.redis.lpush('spiker:processing', task_id)
        self.processing.append(task_id)
        if worker_id:
            self.redis.sadd('spiker:worker_{}:tasks'.format(worker_id), task_id)
            self.workers_tasks[worker_id].add(task_id)
            self.redis.hset('spiker:task_on_worker', task_id, worker_id)
            self.task_on_worker[task_id] = worker_id
        return self.tasks[task_id]

    def get_task_by_id(self, task_id):
        return self.tasks.get(task_id)

    def is_task_processing(self, task_id):
        if task_id not in self.tasks:
            return
        return task_id in self.processing

    def cancel_task(self, task_id):
        if task_id not in self.tasks:
            return
        if task_id not in self.processing:
            return
        self.redis.lrem('spiker:processing', task_id)
        self.redis.lpush('spiker:waiting', task_id)
        self.processing.remove(task_id)
        self.waiting.append(task_id)
        self.remove_worker_task(task_id)
        return True

    def remove_worker_task(self, task_id):
        if task_id in self.task_on_worker:
            worker_id = self.task_on_worker[task_id]
            self.redis.srem('spiker:worker_{}:tasks'.format(worker_id), task_id)
            self.workers_tasks[worker_id].remove(task_id)
            self.redis.hdel('spiker:task_on_worker', task_id)
            del self.task_on_worker[task_id]

    def get_task_worker(self, task_id):
        return self.task_on_worker.get(task_id)

    def cancel_worker_tasks(self, worker_id):
        if worker_id not in self.workers_tasks:
            return
        tasks = copy.copy(self.workers_tasks[worker_id])
        for task_id in tasks:
            self.cancel_task(task_id)
        self.redis.delete('spiker:worker_{}:tasks'.format(worker_id))
        del self.workers_tasks[worker_id]
        return True

    def restore(self):
        # tasks body
        self.tasks.sync()

        # tasks queue
        self.waiting = deque(self.redis.lrange('spiker:waiting', 0, -1))
        self.processing = deque(self.redis.lrange('spiker:processing', 0, -1))

        # tasks processing map
        for worker_id in self.redis.smembers('spiker:workers'):
            self.workers_tasks[worker_id] = self.redis.smembers('spiker:worker_{}:tasks'.format(worker_id))
        self.task_on_worker = self.redis.hgetall('spiker:task_on_worker')

if __name__ == '__main__':
    import unittest
    import random
    from redis import Redis

    class TasksTest(unittest.TestCase):
        def setUp(self):
            # mockRedis лагает на множествах, поэтому тестируем на живом редисе, но в отдельной базе
            self.redis = Redis(db=3)
            self.tasks = Tasks(redis=self.redis)

        def tearDown(self):
            self.redis.flushdb()

        def get_task(self):
            return Task(id=random.randint(100,999), request=Request(url='http://example.com'))

        def test_task_put_and_get(self):
            task = self.get_task()
            self.assertIsNone(self.tasks.get_task())
            self.tasks.put_task(task)
            self.assertFalse(self.tasks.is_task_processing(task.id))
            self.assertEqual(self.tasks.get_task(), task)
            self.assertTrue(self.tasks.is_task_processing(task.id))
            self.tasks.cancel_task(task.id)
            self.assertFalse(self.tasks.is_task_processing(task.id))
            self.tasks.sync()

        def test_task_worker_add_and_remove(self):
            task = self.get_task()
            self.assertTrue(self.tasks.put_task(task))
            self.assertEqual(self.tasks.get_task(worker_id='worker'), task)
            self.assertEqual(self.tasks.get_task_worker(task.id), 'worker')

            self.assertTrue(self.tasks.cancel_task(task.id))
            self.assertIsNone(self.tasks.get_task_worker(task.id))

            self.assertEqual(self.tasks.get_task(worker_id='worker'), task)
            self.assertTrue(self.tasks.remove_task(task.id))
            self.assertIsNone(self.tasks.get_task_worker(task.id))

        def test_load_and_sync(self):
            self.tasks.restore()
            self.tasks.sync()

    unittest.main()