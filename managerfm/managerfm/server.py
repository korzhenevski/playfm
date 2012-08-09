# -*- coding: utf-8 -*-

import gevent
import json
import pymongo
import logging
from pprint import pprint
from gevent_zeromq import zmq
from gevent.queue import Queue
from bson.objectid import ObjectId
from rvlib import pb_safe_parse, WorkerRequest, ManagerResponse, StreamStatus, Job, JobEvent, JobEventResponse
from binascii import hexlify

class ManagerServer(object):
    def __init__(self, endpoint_config, track_factory, db, redis):
        self.endpoint = endpoint_config
        self.context = zmq.Context()
        self.db = db
        self.streams = {}
        self.jobs = {}
        self.queue = set()
        self.job_id = 0
        self.tf_queue = Queue()
        self.redis = redis
        self.track_factory = track_factory

    def subscribe_to_cometfm_firehose(self):
        logging.info('waiting for cometfm status updates...')

        self.cometfm_firehose = self.context.socket(zmq.SUB)
        self.cometfm_firehose.setsockopt(zmq.SUBSCRIBE, 'STATE')
        self.cometfm_firehose.connect(self.endpoint['cometfm_firehose'])

        logging.debug('cometfm firehose endpoint: %s', self.endpoint['cometfm_firehose'])

        while True:
            stream_status = pb_safe_parse(StreamStatus, self.cometfm_firehose.recv())
            if not stream_status:
                logging.error('broken stream status message')
                continue

            station_id, stream_id = stream_status.channel.split('_')
            if stream_status.status == StreamStatus.ONLINE:
                self.put_stream(stream_id, stream_status.channel)


    def remove_stream(self, stream_id):
        if stream_id not in self.streams:
            return
        logging.info('remove stream %s', stream_id)
        stream = self.streams[stream_id]
        if stream['job_id']:
            self.cancel_job(stream['job_id'])
        self.streams.pop(stream_id)
        self.queue.remove(stream_id)

    def put_stream(self, stream_id, channel):
        if stream_id in self.streams:
            return
        logging.info('put stream %s', stream_id)
        self.streams[stream_id] = {
            'id': stream_id,
            'hearbeat_at': None,
            'job_id': None,
            'channel': channel,
        }
        self.queue.add(stream_id)

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
        return self.db.streams.find_one({'_id': ObjectId(stream_id)})

    def get_job_for_worker(self, worker_id):
        if not self.queue:
            return
        stream_id = self.queue.pop()
        print 'find stream %s' % stream_id
        stream = self.find_stream(stream_id)
        if not stream:
            print 'no stream'
            return
        self.job_id += 1
        job_id = str(self.job_id)
        self.jobs[job_id] = stream_id
        return {
            'id': job_id,
            'url': stream['url'],
        }

    def run(self):
        gevent.joinall([
            gevent.spawn(self.job_router),
            gevent.spawn(self.worker_event_receiver),
            gevent.spawn(self.subscribe_to_cometfm_firehose),
            gevent.spawn(self.track_factory_processor),
        ])

    def job_router(self):
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

                logging.debug('worker %s manager response - %s', hexlify(worker_id), response)
                sock.send_multipart([worker_id, '', response.SerializeToString()])

            gevent.sleep()

    def recv_request(self, sock):
        request = sock.recv_multipart()
        # skip envelope empty frame
        return request[0], request[2:]

    def worker_event_receiver(self):
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
        if event.type == JobEvent.META:
            channel = self.streams[self.jobs[event.job_id]]['channel']
            self.tf_queue.put((channel, unicode(event.meta)))
        return True

    def track_factory_processor(self):
        sock = self.context.socket(zmq.PUB)
        sock.bind(self.endpoint['cometfm_events'])
        # wait for subs connect
        gevent.sleep(1)
        for channel, rawmeta in self.tf_queue:
            print channel, rawmeta

            track = self.track_factory.build_track_from_stream_title(rawmeta)
            track['id'] = str(self.db.tracks.insert(track))
            if track:
                pprint(track)
                self.update_onair(channel, track)
                sock.send_multipart([channel, ''])


    def update_onair(self, channel, track):
        # and build short onair track info
        onair_fields = ('id', 'title', 'artist', 'name', 'image_cover')
        onair = dict([(key, str(val)) for key, val in track.iteritems() if key in onair_fields])
        # avoid duplicate
        # if onair['artist'] and onair['name']:
        #    onair.pop('title')
        self.redis.hmset('channel:%s' % channel, onair)

