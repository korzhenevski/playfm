#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import logging
import json
import os
from gevent_zeromq import zmq
from gevent.queue import Queue
from rvlib import pb_safe_parse, pb_dump, WorkerRequest, ManagerResponse,\
    StreamStatus, Job, JobEvent, JobEventResponse, OnairUpdate, Track
from binascii import hexlify
from time import time
from zlib import crc32
from datetime import datetime
from tempfile import NamedTemporaryFile

def fasthash(data):
    return crc32(data) & 0xffffffff

def humanize_worker_id(worker_id):
    worker_id = hexlify(worker_id)
    if len(worker_id) < 8:
        return worker_id
    return '%s..%s' % (worker_id[:4], worker_id[-4:])

class ManagerServer(object):
    SNAPSHOT_VERSION = 2
    TOUCH_DEADLINE = 20
    HEARTBEAT_DEADLINE = 10

    def __init__(self, endpoint_config, track_factory, db, redis, snapshot_file):
        self.endpoint = endpoint_config
        self.context = zmq.Context()
        self.db = db
        self.streams = {}
        self.queue = set()
        self.job_id = 0
        self.jobs = {}
        self.redis = redis
        self.track_factory = track_factory
        self.track_cache = {}
        self.stream_title_cache = {}
        self.stream_meta = Queue()
        self.snapshot_file = snapshot_file

    def watch_cometfm_firehose(self):
        firehose = self.context.socket(zmq.SUB)
        firehose.setsockopt(zmq.SUBSCRIBE, 'STATUS')
        firehose.connect(self.endpoint['cometfm_firehose'])

        logging.debug('cometfm firehose endpoint: %s', self.endpoint['cometfm_firehose'])
        while True:
            topic = firehose.recv()
            status = pb_safe_parse(StreamStatus, firehose.recv())

            if status.type == StreamStatus.ONLINE:
                self.put_stream(status.stream_id, station_id=status.station_id, on_demand=True)

            if status.type == StreamStatus.TOUCH:
                self.touch_stream(status.stream_id, clients=status.clients)

    def touch_stream(self, stream_id, clients):
        if stream_id not in self.streams:
            return
        logging.debug('touch stream %s, current clients %s', stream_id, clients)
        self.streams[stream_id].update({
            'clients': clients,
            'touch_at': time()
        })

    def put_stream(self, stream_id, station_id, on_demand):
        if stream_id in self.streams:
            return
        logging.info('put stream %s', stream_id)
        self.streams[stream_id] = {
            'stream_id': stream_id,
            'station_id': station_id,
            'on_demand': on_demand,
            'clients': None,
            'touch_at': time(),
            'job_id': None,
            'hb_at': None,
        }
        self.queue.add(stream_id)

    def cleanup_ondemand_streams(self):
        while True:
            current_time = time()
            stream_ids = set()
            for stream_id, stream in self.streams.iteritems():
                if not stream['on_demand']:
                    continue
                touch_deadline = stream['touch_at'] and current_time - stream['touch_at'] >= self.TOUCH_DEADLINE
                if touch_deadline or stream['clients'] == 0:
                    stream_ids.add(stream_id)
            for stream_id in stream_ids:
                logging.info('remove ondemand stream %s', stream_id)
                self.remove_stream(stream_id)
            gevent.sleep(20)

    def check_jobs_heartbeat(self):
        while True:
            current_time = time()
            for stream_id, stream in self.streams.iteritems():
                hb_at = stream['hb_at']
                if hb_at and current_time - hb_at >= self.HEARTBEAT_DEADLINE:
                    logging.info('requeue stream %s caused by expired hb deadline', stream_id)
                    self.streams[stream_id]['hb_at'] = current_time
                    self.cancel_job(stream['job_id'])
                    self.queue.add(stream_id)
            gevent.sleep(5)

    def get_snapshot_name(self):
        return '%s.%s' % (self.snapshot_file, self.SNAPSHOT_VERSION)        

    def dump_snapshot(self):
        if not self.snapshot_file:
            logging.info('snapshot disabled')
            return
        self.load_snapshot()
        while True:
            gevent.sleep(30)
            snapshot = NamedTemporaryFile(prefix='mfm-snapshot-', delete=False)
            for stream in self.streams.itervalues():
                keys = ('stream_id', 'station_id', 'on_demand')
                stream = dict(zip(keys, (stream[key] for key in keys)))
                snapshot.file.write(json.dumps(stream) + '\n')
            snapshot.file.flush()
            os.fsync(snapshot.file.fileno())
            snapshot.close()
            name = self.get_snapshot_name()
            logging.debug('dump snapshot to %s', name)
            os.rename(snapshot.name, name)

    def load_snapshot(self):
        name = self.get_snapshot_name()
        if not os.path.exists(name):
            return
        logging.debug('load snapshot from %s', name)
        with open(name) as snapshot:
            for item in snapshot:
                stream = json.loads(item.strip())
                self.put_stream(**stream)

    def remove_stream(self, stream_id):
        if stream_id not in self.streams:
            return
        logging.info('remove stream %s', stream_id)
        stream = self.streams[stream_id]
        if stream['job_id']:
            self.cancel_job(stream['job_id'])
        self.streams.pop(stream_id)
        if stream_id in self.queue:
            self.queue.remove(stream_id)

    def cancel_job(self, job_id):
        if job_id not in self.jobs:
            return
        logging.debug('cancel job %s', job_id)
        stream_id = self.jobs.pop(job_id)
        if self.streams[stream_id].get('job_id') == job_id:
            self.streams[stream_id]['job_id'] = None

    def find_stream(self, stream_id):
        return self.db.streams.find_one({'id': stream_id, 'deleted_at': 0})

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
        self.streams[stream_id].update({
            'job_id': job_id,
            'hb_at': time()
        })

        job = Job()
        job.id = job_id
        job.url = stream['url']

        return job

    def run(self):
        gevent.joinall([
            gevent.spawn(self.cleanup_ondemand_streams),
            gevent.spawn(self.dump_snapshot),
            gevent.spawn(self.check_jobs_heartbeat),
            gevent.spawn(self.dispatch_jobs),
            gevent.spawn(self.process_worker_events),
            gevent.spawn(self.watch_cometfm_firehose),
            gevent.spawn(self.process_stream_meta),
            ])

    def dispatch_jobs(self):
        logging.info('job router started...')

        sock = self.context.socket(zmq.ROUTER)
        sock.bind(self.endpoint['worker_manager'])

        logging.debug('worker manager endpoint: %s', self.endpoint['worker_manager'])
        while True:
            worker_id, payload = self.recv_request(sock)
            #logging.debug('message from worker %s', hexlify(worker_id))
            request = pb_safe_parse(WorkerRequest, payload)
            if not request:
                logging.error('broken worker request message')
                continue

            if request.type == WorkerRequest.READY:
                response = ManagerResponse()
                job = self.get_job_for_worker(worker_id)
                if job:
                    response.status = ManagerResponse.JOB
                    response.job.MergeFrom(job)
                    logging.info('job %s for worker %s', job.id, humanize_worker_id(worker_id))
                else:
                    response.status = ManagerResponse.WAIT

                #logging.debug('worker %s manager response - %s', hexlify(worker_id), str(response).strip())
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

            logging.debug('worker %s job event %s - %s',
                humanize_worker_id(worker_id),
                pb_dump(job_event), pb_dump(response))
            sock.send_multipart([worker_id, '', response.SerializeToString()])
            gevent.sleep()

    def process_job_event(self, event):
        if event.job_id not in self.jobs:
            return False
        stream_id = self.jobs[event.job_id]
        if event.type == JobEvent.META:
            stream = self.streams[stream_id]
            self.stream_meta.put((stream['stream_id'], stream['station_id'], event.meta))
        if event.type == JobEvent.HEARTBEAT:
            self.streams[stream_id]['hb_at'] = time()
        if event.type == JobEvent.ERROR:
            logging.warning('Job error: %s', event.error)
        return True

    def process_stream_meta(self):
        cometfm = self.context.socket(zmq.PUB)
        cometfm.connect(self.endpoint['cometfm_events'])
        # wait for subscribers connect
        gevent.sleep(1)

        for stream_id, station_id, meta in self.stream_meta:
            stream_title = self.track_factory.parse_stream_title(meta)
            if not stream_title:
                continue

            # воркер присылает сырую мету, кешируем повторения
            title_hash = fasthash(stream_title)
            if self.track_cache.get(stream_id) == title_hash:
                continue
            
            self.track_cache[stream_id] = title_hash
            
            logging.debug('stream title: "%s"', stream_title)
            track = self.track_factory.build_track(stream_title)
            if not track:
                logging.warning('build track failed')
                continue

            track['hash'] = fasthash(track['title'].lower())
            exists_track = self.db.tracks.find_one({'hash': track['hash']})
            if exists_track:
                track = exists_track
            else:
                track['id'] = self.db.object_ids.find_and_modify(
                    {'_id': 'tracks'}, {'$inc': {'next': 1}},
                    new=True, upsert=True
                )['next']
                self.db.tracks.insert(track)

            self.db.onair_history.insert({
                'stream_id': stream_id,
                'station_id': station_id,
                'track_id': track['id'],
                'tags': track['tags'],
                'created_at': datetime.now(),
            })

            update = OnairUpdate()
            update.stream_id = stream_id
            update.station_id = station_id
            for field in ('id', 'title', 'artist', 'name', 'image_url'):
                setattr(update.track, field, track.get(field))

            cometfm.send(update.SerializeToString())
