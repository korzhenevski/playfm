# -*- coding: utf-8 -*-

import logging
import gevent
from gevent.queue import Queue
from gevent.pool import Pool
from gevent_zeromq import zmq
from workerfm.radio import Radio, RadioReadError


class Worker(object):
    def __init__(self, endpoint, maxjobs):
        self.events = Queue()
        self.thread_pool = Pool(size=maxjobs)
        self.jobs = {}
        self.context = zmq.Context()
        self.endpoint = endpoint

    def worker(self):
        self.manager_socket = self.context.socket(zmq.REQ)
        self.manager_socket.connect(self.endpoint['manager_jobs'])

        logging.info('worker ready for jobs')
        logging.info('manager jobs endpoint: %s', self.endpoint['manager_jobs'])

        while True:
            self.thread_pool.wait_available()

            request = WorkerRequest()
            request.type = WorkerRequest.READY
            self.manager_socket.send(request.SerializeToString())

            manager_response = pb_safe_parse(ManagerResponse, self.manager_socket.recv())
            if not manager_response:
                logging.error('broken manager response')
                continue

            #logging.debug('manager response - %s', str(manager_response).strip())
            if manager_response.status == ManagerResponse.JOB:
                job = manager_response.job
                worker_thread = WorkerThread(job.id, url=job.url, manager=self)
                worker_thread.greenlet = self.thread_pool.spawn(worker_thread.run)
                self.jobs[job.id] = worker_thread
                logging.info('job %s: %s', job.id, job.url)
                logging.debug('thread pool free count: %s', self.thread_pool.free_count())

            if manager_response.status == ManagerResponse.WAIT:
                gevent.sleep(1)

            gevent.sleep()

    def event_sender(self):
        self.events_socket = self.context.socket(zmq.REQ)
        self.events_socket.connect(self.endpoint['manager_events'])

        logging.debug('manager events endpoint: %s', self.endpoint['manager_events'])
        logging.info('wait for thread events...')

        for event in self.events:
            logging.debug('event - %s', pb_dump(event))
            if event.job_id not in self.jobs:
                logging.debug('event dropped')
                continue

            self.events_socket.send(event.SerializeToString())
            event_response = pb_safe_parse(JobEventResponse, self.events_socket.recv())
            if not event_response:
                logging.error('broken job event response')
                continue

            if event_response.status == JobEventResponse.JOB_GONE:
                logging.info('job %s gone, kill thread.', event.job_id)
                # TODO: нужна-ли эта проверка?
                #if event.job_id in self.jobs:
                try:
                    thread = self.jobs[event.job_id]
                    thread.stop()
                    self.thread_pool.killone(thread.greenlet)
                except Exception as exc:
                    logging.error('error while stoping thread: %s', exc)
            else:
                logging.debug('event sent ok')

    def job_error(self, job_id, error):
        event = JobEvent()
        event.job_id = job_id
        event.type = JobEvent.ERROR
        event.error = error
        self.events.put(event)

    def job_heartbeat(self, job_id):
        event = JobEvent()
        event.job_id = job_id
        event.type = JobEvent.HEARTBEAT
        self.events.put(event)

    def job_meta(self, job_id, meta):
        event = JobEvent()
        event.job_id = job_id
        event.type = JobEvent.META
        event.meta = meta
        self.events.put(event)

class WorkerThread(object):
    def __init__(self, job_id, url, manager):
        self.job_id = job_id
        self.url = url
        self.manager = manager
        self.error = None
        self.meta = None

    def run(self):
        self.running = True
        gevent.joinall([
            gevent.spawn(self.listen),
            gevent.spawn(self.heatbeat)
        ])

    def stop(self):
        self.running = False
        self.radio.disconnect()

    def listen(self, default_timeout=2, max_timeout=10):
        self.radio = Radio(self.url)
        timeout = default_timeout
        while self.running:
            self.error = None
            self.meta = None
            try:
                self.radio.connect()
                # reset after success connect
                timeout = default_timeout
                for meta in self.radio.stream_meta():
                    self.manager.job_meta(self.job_id, meta)
            except Exception as exc:
                # skip socket error while disconnect
                if isinstance(exc, RadioReadError) and not self.running:
                    continue
                self.manager.job_error(self.job_id, str(exc))
                # incremental timeout
                if timeout > max_timeout:
                    timeout = max_timeout
                else:
                    timeout = int(timeout * 1.5)
                gevent.sleep(timeout)
        self.radio.disconnect()

    def heatbeat(self):
        while self.running:
            self.manager.job_heartbeat(self.job_id)
            gevent.sleep(5)

class MockManager(object):
    def job_heartbeat(self, job_id):
        print 'job %s hb' % job_id

    def job_error(self, job_id, error):
        print 'job %s error: %s' % (job_id, error)

    def job_meta(self, job_id, meta):
        print 'job %s meta: %s' % (job_id, meta)
