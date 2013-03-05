#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import logging
import gevent_zeromq as zmq
import google.protobuf.message
from .controller import BrokerController
from .spike_pb2 import TaskAction, TaskResult, ActionResult, BrokerResponse


class BrokerServer:
    def __init__(self, redis, consumer_addr, workers_addr, workers_results_addr):
        self.redis = redis
        self.broker = BrokerController(redis=self.redis)
        self.context = zmq.Context()

        # запросы от клиентов
        self.consumer_addr = consumer_addr
        # запросы от работников
        self.workers_addr = workers_addr
        # результаты от работников
        self.workers_results_addr = workers_results_addr

    def handle_consumers(self):
        logging.info('handle consumers on %s', self.consumer_addr)

        self.consumers = self.context.socket(zmq.ROUTER)
        self.consumers.bind(self.consumer_addr)

        for consumer_id, task_action in self.socket_reader(self.consumers, TaskAction):
            result = ActionResult(task_id=task_action.task.id)
            try:
                self.broker.task_action(task_action)
            except Exception as exc:
                result.error = str(exc)
            self.consumers.send_multipart([consumer_id, '', result.SerializeToString()])

    def handle_workers(self):
        logging.info('handle workers on %s', self.workers_addr)

        self.workers = self.context.socket(zmq.ROUTER)
        self.workers.bind(self.workers_addr)

        # здесь можно принимать статистику от воркера
        for worker_id, request in self.socket_reader(self.workers):
            task = self.broker.get_task_for_worker(worker_id)
            response = BrokerResponse(status=BrokerResponse.OK)
            if task:
                response.task.MergeFrom(task)
                response.status = BrokerResponse.TASK
            self.workers.send_multipart([worker_id, '', response.SerializeToString()])

    def handle_workers_results(self):
        logging.info('handle workers results on %s', self.workers_results_addr)

        self.workers_results = self.context.socket(zmq.ROUTER)
        self.workers_results.bind(self.workers_results_addr)

        for worker_id, task_result in self.socket_reader(self.workers_results, TaskResult):
            logging.debug(str(task_result))
            response = BrokerResponse(status=BrokerResponse.TASK_GONE)
            if self.broker.worker_task_result(worker_id, task_result):
                response.status = BrokerResponse.OK
            self.workers_results.send_multipart([worker_id, '', response.SerializeToString()])

    def socket_reader(self, sock, message_class=None):
        while True:
            msg = sock.recv_multipart()
            # насколько важна эта проверка?
            if len(msg) < 3:
                logging.debug('invalid packet')
                continue
            message = msg[2]
            if message_class:
                message = self.pb_safe_decode(message_class, message)
            if not message:
                continue
            yield msg[0], message
            gevent.sleep()

    def pb_safe_decode(self, klass, raw):
        try:
            return klass.FromString(raw)
        except google.protobuf.message.DecodeError:
            logging.exception('protobuf decode error')

    def run(self):
        gevent.joinall([
            gevent.spawn(self.handle_consumers),
            gevent.spawn(self.handle_workers),
            gevent.spawn(self.handle_workers_results),
            gevent.spawn(self.monitor),
        ])

    def monitor(self):
        import psutil
        import os
        process = psutil.Process(os.getpid())

        while True:
            self.broker.purge_dead_workers()
            #logging.info('workers: %s, waiting: %s, processing: %s',
            #    len(self.broker.workers), len(self.broker.tasks.waiting), len(self.broker.tasks.processing))
            gevent.sleep(1)
