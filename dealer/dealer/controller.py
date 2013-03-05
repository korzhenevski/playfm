#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from tasks import Tasks
from spike_pb2 import Task, TaskAction, TaskResult

class WorkersSet(set):
    def __init__(self, redis):
        self.redis = redis
        self.keyspace = 'spiker:workers'
        self.update(self.redis.smembers(self.keyspace))

    def add(self, worker_id):
        # кеширование добавления ?
        if worker_id not in self:
            self.redis.sadd(self.keyspace, worker_id)
        super(WorkersSet, self).add(worker_id)

    def remove(self, worker_id):
        self.redis.srem(self.keyspace, worker_id)
        super(WorkersSet, self).remove(worker_id)

    def drop(self):
        self.redis.delete(self.keyspace)
        self.update([])

class BrokerController:
    def __init__(self, redis, restore_runtime=True):
        self.redis = redis
        redis.flushall()
        self.tasks = Tasks(redis=self.redis)
        self.workers = WorkersSet(redis=self.redis)
        self.workers_pulse = {}
        if restore_runtime:
            self.tasks.restore()
            # даем возможность переподключиться воркерам при перезагрузке менеджера
            for worker_id in self.workers:
                self.workers_pulse[worker_id] = time.time()
        else:
            self.workers.drop()

    def task_action(self, task_action):
        assert isinstance(task_action, TaskAction)

        if task_action.action == TaskAction.PUT:
            if not task_action.task.IsInitialized():
                raise ValueError('Task is required for PUT action')
            return self.tasks.put_task(task_action.task)

        if task_action.action == TaskAction.CANCEL:
            return self.tasks.cancel_task(task_action.task.id)

        if task_action.action == TaskAction.REMOVE:
            return self.tasks.remove_task(task_action.task.id)

    def get_task_for_worker(self, worker_id):
        self.register_worker(worker_id)
        task = self.tasks.get_task(worker_id)
        return task

    def worker_task_result(self, worker_id, task_result):
        self.register_worker(worker_id)
        # игнорируем результат, если задача снята или работает на другом воркере
        if self.tasks.get_task_worker(task_result.task_id) != worker_id:
            return
        task = self.tasks.get_task_by_id(task_result.task_id)
        if not task:
            return

        #if task_result.type in (TaskResult.RESPONSE, TaskResult.ERROR):
        #    self.tasks.remove_task(task_result.task_id)

        result = task_result.SerializeToString()
        self.redis.lpush('{}:{}'.format(task.consumer, task.id), result)
        self.redis.publish('{}'.format(task.consumer), result)
        return True

    def worker_stat(self, worker_stat):
        # заглушка под обработку статистики с воркера
        pass

    def register_worker(self, worker_id):
        self.workers.add(worker_id)
        self.workers_pulse[worker_id] = time.time()

    def unregister_worker(self, worker_id):
        # снимаем задачи с воркера
        self.tasks.cancel_worker_tasks(worker_id)
        # удаляем из списка
        if worker_id in self.workers:
            self.workers.remove(worker_id)
        del self.workers_pulse[worker_id]

    def purge_dead_workers(self, timeout=3):
        workers = [wid for wid, ts in self.workers_pulse.iteritems() if time.time() >= ts + timeout]
        for wid in workers:
            self.unregister_worker(wid)
        return workers


if __name__ == '__main__':
    import unittest
    from random import randint
    from mockredis import MockRedis
    from redis import Redis

    class BrokerControllerTest(unittest.TestCase):
        def setUp(self):
            # mockRedis лагает на множествах, поэтому тестируем на живом редисе, но в отдельной базе
            self.redis = Redis(db=3)
            self.broker = BrokerController(redis=self.redis)

        def tearDown(self):
            self.redis.flushdb()

        def test_task_action(self):
            task = self.mock_task()
            action = TaskAction(action=TaskAction.PUT)

            with self.assertRaises(ValueError):
                self.broker.task_action(action)

            action.task.MergeFrom(task)
            self.assertTrue(self.broker.task_action(action))
            self.assertFalse(self.broker.task_action(action))

            action = TaskAction(task=task, action=TaskAction.CANCEL)
            self.assertIsNone(self.broker.task_action(action))

            action = TaskAction(task=task, action=TaskAction.REMOVE)
            self.assertTrue(self.broker.task_action(action))


        def test_purge_dead_workers(self):
            task = self.mock_task()
            self.assertTrue(self.broker.tasks.put_task(task))
            self.assertEqual(self.broker.get_task_for_worker('worker'), task)
            self.assertTrue(self.broker.tasks.is_task_processing(task.id))
            self.assertListEqual(self.broker.purge_dead_workers(timeout=-1), ['worker'])

        def mock_task(self):
            return Task(id=randint(1000, 9999))

    unittest.main()
