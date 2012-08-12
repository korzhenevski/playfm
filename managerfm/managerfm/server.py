# -*- coding: utf-8 -*-

import gevent
import logging
from gevent_zeromq import zmq
from gevent.queue import Queue
from rvlib import pb_safe_parse, WorkerRequest, ManagerResponse,\
    StreamStatus, Job, JobEvent, JobEventResponse, OnairUpdate, Track
from binascii import hexlify
from time import time
from zlib import crc32

class ManagerServer(object):
    def __init__(self, endpoint_config, track_factory, db, redis):
        self.endpoint = endpoint_config
        self.context = zmq.Context()
        self.db = db
        self.streams = {}
        self.jobs = {}
        self.queue = set()
        self.job_id = 0
        self.stream_meta_queue = Queue()
        self.redis = redis
        self.track_factory = track_factory
        self.track_cache = {}

    def watch_cometfm_firehose(self):
        logging.info('waiting for cometfm status updates...')

        firehose = self.context.socket(zmq.SUB)
        firehose.setsockopt(zmq.SUBSCRIBE, 'STATE')
        firehose.connect(self.endpoint['cometfm_firehose'])

        logging.debug('cometfm firehose endpoint: %s', self.endpoint['cometfm_firehose'])

        while True:
            topic = firehose.recv()
            status = pb_safe_parse(StreamStatus, firehose.recv())
            if not status:
                logging.error('broken stream status message')
                continue

            if status.status == StreamStatus.ONLINE:
                self.put_stream(status.stream_id, station_id=status.station_id)

    def put_stream(self, stream_id, station_id):
        if stream_id in self.streams:
            return
        logging.info('put stream %s', stream_id)
        self.streams[stream_id] = {
            'id': stream_id,
            'hearbeat_at': None,
            'station_id': station_id,
            'job_id': None,
        }
        self.queue.add(stream_id)

    def remove_stream(self, stream_id):
        if stream_id not in self.streams:
            return
        logging.info('remove stream %s', stream_id)
        stream = self.streams[stream_id]
        if stream['job_id']:
            self.cancel_job(stream['job_id'])
        self.streams.pop(stream_id)
        self.queue.remove(stream_id)

    def cancel_job(self, job_id):
        if job_id not in self.jobs:
            return
        logging.debug('cancel job %s', job_id)
        stream_id = self.jobs.pop(job_id)
        self.streams[stream_id].update({
            'hearbeat_at': None,
            'job_id': None
        })

    def find_stream(self, stream_id):
        return self.db.streams.find_one({'id': stream_id})

    def get_job_for_worker(self, worker_id):
        if not self.queue:
            return
        stream_id = self.queue.pop()
        logging.debug('find stream %s', stream_id)
        stream = self.find_stream(stream_id)
        if not stream:
            logging.debug('stream %s not exists', stream_id)
            return
        self.job_id += 1
        job_id = self.job_id
        self.jobs[job_id] = stream_id
        return {
            'id': job_id,
            'url': stream['url'],
        }

    def run(self):
        gevent.joinall([
            gevent.spawn(self.dispatch_jobs),
            gevent.spawn(self.process_worker_events),
            gevent.spawn(self.watch_cometfm_firehose),
            gevent.spawn(self.process_stream_meta),
            gevent.spawn(self.process_stream_meta),
            gevent.spawn(self.process_stream_meta),
        ])

    def dispatch_jobs(self):
        logging.info('job router started...')

        sock = self.context.socket(zmq.ROUTER)
        sock.bind(self.endpoint['worker_manager'])

        logging.debug('worker manager endpoint: %s', self.endpoint['worker_manager'])
        while True:
            worker_id, payload = self.recv_request(sock)
            logging.debug('message from worker %s', hexlify(worker_id))
            request = pb_safe_parse(WorkerRequest, payload)
            if not request:
                logging.error('broken worker request message')
                continue

            if request.type == WorkerRequest.READY:
                response = ManagerResponse()
                job = self.get_job_for_worker(worker_id)
                if job:
                    response.status = ManagerResponse.JOB
                    response.job.id = job['id']
                    response.job.url = job['url']
                    logging.info('job %s for worker %s', job['id'], hexlify(worker_id))
                else:
                    response.status = ManagerResponse.WAIT

                logging.debug('worker %s manager response - %s', hexlify(worker_id), str(response).strip())
                sock.send_multipart([worker_id, '', response.SerializeToString()])

            gevent.sleep()

    def recv_request(self, sock):
        request = sock.recv_multipart()
        # skip envelope empty frame
        return request[0], request[2]

    def process_worker_events(self):
        logging.info('manager wait for worker events...')

        sock = self.context.socket(zmq.ROUTER)
        sock.bind(self.endpoint['worker_events'])
        logging.info('worker events endpoint: %s', self.endpoint['worker_events'])

        while True:
            worker_id, payload = self.recv_request(sock)
            job_event = pb_safe_parse(JobEvent, payload)
            if not job_event:
                logging.error('broken job event')

            response = JobEventResponse()
            if self.process_job_event(job_event):
                response.status = JobEventResponse.OK
            else:
                response.status = JobEventResponse.JOB_GONE

            logging.debug('worker %s job event response - %s', hexlify(worker_id), response)
            sock.send_multipart([worker_id, '', response.SerializeToString()])
            gevent.sleep()

    def process_job_event(self, event):
        if event.job_id not in self.jobs:
            return False
        stream_id = self.jobs[event.job_id]
        if event.type == JobEvent.META:
            stream = self.streams[stream_id]
            self.stream_meta_queue.put({
                'stream_id': stream['id'],
                'station_id': stream['station_id'],
                'meta': event.meta
            })
        if event.type == JobEvent.HEARTBEAT:
            self.streams[stream_id]['hearbeat_at'] = time()
        if event.type == JobEvent.ERROR:
            logging.warning('Job error: %s', event.error)
        return True

    def process_stream_meta(self):
        cometfm = self.context.socket(zmq.PUB)
        cometfm.connect(self.endpoint['cometfm_events'])
        # wait for subscribers connect
        gevent.sleep(1)

        for request in self.stream_meta_queue:
            stream_title = self.track_factory.parse_stream_title(request['meta'])
            if not stream_title:
                continue

            # воркер присылает сырую мету, кешируем повторения
            cache_hash = crc32(stream_title) & 0xffffffff
            if self.track_cache.get(request['stream_id']) == cache_hash:
               continue

            logging.debug('stream title: "%s"', stream_title)
            track = self.track_factory.build_track(stream_title)
            if not track:
                continue

            track['id'] = self.db.object_ids.find_and_modify(
                {'_id': 'tracks'}, {'$inc': {'next': 1}},
                new=True, upsert=True)['next']
            self.db.tracks.insert(track)
            self.track_cache[request['stream_id']] = cache_hash

            update = OnairUpdate()
            update.stream_id = request['stream_id']
            update.station_id = request['station_id']
            for field in ('id', 'title', 'artist', 'name', 'image_url'):
                setattr(update.track, field, track.get(field))
            cometfm.send(update.SerializeToString())
