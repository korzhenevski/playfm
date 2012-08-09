# -*- coding: utf-8 -*-

import gevent
import json
from gevent.monkey import patch_all
patch_all()
import pymongo
import redis
import logging
from pprint import pprint
from gevent_zeromq import zmq
from gevent.queue import Queue
from bson.objectid import ObjectId

class ManagerServer(object):
    def __init__(self, endpoint_config, track_factory, db, redis):
        self.endpoint_config = endpoint_config
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
        logging.info('subscribe to cometfm firehose')
        self.cometfm_firehose = self.context.socket(zmq.SUB)
        self.cometfm_firehose.setsockopt(zmq.SUBSCRIBE, 'STATE')
        self.cometfm_firehose.connect(self.endpoint_config['cometfm_firehose'])
        logging.debug('cometfm firehose endpoint: %s', self.endpoint_config['cometfm_firehose'])
        while True:
            payload = self.cometfm_firehose.recv_multipart()
            if len(payload) != 3:
                continue
            topic, channel, is_active = payload
            logging.debug('cometfm received message: %s', payload)
            station_id, stream_id = channel.split('_')
            if is_active == '1':
                self.put_stream(stream_id, channel)
            else:
                pass
                #self.remove_stream(stream_id)

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
        sock = self.context.socket(zmq.ROUTER)
        sock.bind(self.endpoint_config['worker_manager'])
        while True:
            worker_id, cmd, payload = self.recv_request(sock)
            print cmd
            if cmd == 'ready':
                job = self.get_job_for_worker(worker_id)
                if job:
                    job = json.dumps(job)
                    sock.send_multipart([worker_id, '', 'job', job])
                else:
                    sock.send_multipart([worker_id, '', 'wait', ''])
            else:
                print 'invalid cmd'
            gevent.sleep(0)

    def recv_request(self, sock):
        request = sock.recv_multipart()
        worker_id = request[0]
        payload = request[2:]
        cmd = payload[0]
        return worker_id, cmd, payload

    def worker_event_receiver(self):
        sock = self.context.socket(zmq.ROUTER)
        sock.bind(self.endpoint_config['worker_events'])
        while True:
            worker_id, cmd, payload = self.recv_request(sock)
            if cmd != 'job_status':
                print 'invalid event_recv cmd'
                continue
            status = json.loads(payload[2])
            if self.process_job_status(payload[1], status_type=status['type'], data=status['data']):
                reply = '200'
            else:
                reply = '404'
            sock.send_multipart([worker_id, '', reply])
            gevent.sleep(0)

    def process_job_status(self, job_id, status_type, data):
        print 'got job %s, %s: %s' % (job_id, status_type, data)
        if job_id not in self.jobs:
            return False
        if status_type == 'meta':
            channel = self.streams[self.jobs[job_id]]['channel']
            self.tf_queue.put((channel, unicode(data)))
        return True

    def track_factory_processor(self):
        sock = self.context.socket(zmq.PUB)
        sock.bind(self.endpoint_config['cometfm_events'])
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

