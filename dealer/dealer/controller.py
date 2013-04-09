#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from spike_pb2 import Request, Task, TaskResult, _TASKRESULT_TYPE
from protobuf_to_dict import protobuf_to_dict
"""

mongodb tasks
    request
    result:
        result_type
    worker_id
    touch_at
    started_at
"""


class Controller:
    def __init__(self, db):
        self.db = db
        self.tasks = db['tasks']

    def get_task_for_worker(self, worker_id):
        db_task = self.tasks.find_and_modify({'status': 'queued'}, {
            '$set': {'status': 'processing', 'worker_id': worker_id}
        })
        if not db_task:
            return
        task = Task()
        task.id = db_task['_id']
        task.consumer = db_task['consumer']
        task.request.MergeFrom(Request(**db_task['request']))
        return task

    def worker_task_result(self, worker_id, task_result):
        result_type = _TASKRESULT_TYPE.values_by_number[task_result.type].name
        result = protobuf_to_dict(task_result)
        self.tasks.update({'_id': task_result.task_id}, {'$set': {'result': {result_type: result}}})
        #print 'result: worker_id = {}, task_result = {}'.format(worker_id, task_result)

    def worker_stat(self, worker_stat):
        pass

    def register_worker(self, worker_id):
        pass

    def unregister_worker(self, worker_id):
        pass

    def purge_dead_workers(self, timeout=3):
        pass