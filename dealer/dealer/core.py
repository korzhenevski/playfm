#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent_zeromq as zmq
from .controller import Controller
from .spike_pb2 import TaskResult, BrokerResponse
from .utils import RouterSocket


class Dealer(object):
    def __init__(self, db):
        self.db = db
        self.context = zmq.Context()
        self.ctrl = Controller(self.db)

    def run(self, workers_addr, workers_results_addr):
        from gevent.pool import Pool

        pool = Pool()
        pool.spawn(self.handle_workers, workers_addr)
        pool.spawn(self.handle_results, workers_results_addr)
        pool.join()

    def handle_workers(self, endpoint):
        sock = RouterSocket(self.context, endpoint)
        for worker_id, request in sock.reader():
            task = self.ctrl.get_task_for_worker(worker_id)
            response = BrokerResponse(status=BrokerResponse.OK)
            if task:
                response.task.MergeFrom(task)
                response.status = BrokerResponse.TASK
            sock.send(worker_id, response)

    def handle_results(self, endpoint):
        sock = RouterSocket(self.context, endpoint)
        for worker_id, task_result in sock.reader(protobuf_class=TaskResult):
            response = BrokerResponse(status=BrokerResponse.OK)
            self.ctrl.worker_task_result(worker_id, task_result)
            #if self.ctrl.worker_task_result(worker_id, task_result):
            #    response.status = BrokerResponse.OK
            sock.send(worker_id, response)