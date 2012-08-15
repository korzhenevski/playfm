#!/usr/bin/env python

import gevent
from gevent.event import Event as GeventEvent
from gevent_zeromq import zmq
from gevent.queue import Queue
from time import time
from rvlib import pb_safe_parse, pb_dump, OnairUpdate, StreamStatus
import logging

class Server(object):
    def __init__(self, redis, endpoint):
        self.ctx = zmq.Context()
        self.channels = {}
        self.redis = redis
        self.endpoint = endpoint
        self.firehose = Queue()

    def get_channel(self, name):
        if name not in self.channels:
            self.channels[name] = Event(manager=self, channel=name)
        return self.channels.get(name)

    def get_channel_name(self, station_id, stream_id):
        return '%s_%s' % (station_id, stream_id)

    def event_set_state(self, channel, state):
        status = StreamStatus()
        channel = channel.split('_', 1)
        status.station_id, status.stream_id = map(int, channel)
        status.status = StreamStatus.ONLINE if state else StreamStatus.OFFLINE
        self.firehose.put(status)

    def wakeup_channel(self, name):
        channel = self.get_channel(name)
        channel.set()
        channel.clear()

    def run(self):
        gevent.spawn(self.watch_onair_updates)
        #gevent.spawn(self.activity_publisher)
        gevent.spawn(self.firehose_hydrant)

    def get_info(self, station_id, stream_id, user_id, timeout):
        channel = self.get_channel_name(station_id, stream_id)
        if timeout is not None:
            self.get_channel(channel).wait(timeout)
        data = self.redis.hgetall('onair:%s' % channel)
        if user_id and data.get('id'):
            data['faved'] = self.redis.sismember('user:%s:favs' % user_id, data['id'])
        return data

    def watch_onair_updates(self):
        logging.info('subscribe to onair updates...')

        sock = self.ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, '')
        sock.bind(self.endpoint['onair_updates'])

        logging.debug('onair updates endpoint: %s', self.endpoint['onair_updates'])

        while True:
            onair = pb_safe_parse(OnairUpdate, sock.recv())
            if not onair:
                logging.error('broken onair update message')
                pass

            channel = self.get_channel_name(onair.station_id, onair.stream_id)

            # check track duplicate
            """
            track_id = str(onair.track.id)
            track_key = 'onair_track:%s' % channel
            update_id = self.redis.getset(track_key, track_id)
            if update_id == track_id:
                logging.debug('skip duplicate onair track %s', track_id)
                continue
            self.redis.expire(track_key, 60)
            """

            # cache trackinfo and notify comet clients
            logging.info('update onair channel %s', channel)
            cache_track = dict([(k, getattr(onair.track, k)) for k in ('id', 'title', 'artist', 'name', 'image_url')])
            self.redis.hmset('onair:%s' % channel, cache_track)
            self.wakeup_channel(channel)


    """
    def activity_publisher(self):
        while True:
            for channel, event in self.channels.iteritems():
                self.firehose.put(['ACTIVITY', channel, str(event.waiters)])
            gevent.sleep(60)
    """

    def firehose_hydrant(self):
        sock = self.ctx.socket(zmq.PUB)
        sock.bind(self.endpoint['firehose'])
        for message in self.firehose:
            logging.debug('stream status - %s', pb_dump(message))
            sock.send_multipart(['STATE', message.SerializeToString()])

class Event(GeventEvent):
    def __init__(self, manager, channel, *args, **kwargs):
        super(Event, self).__init__(*args, **kwargs)
        self.manager = manager
        self.channel = channel
        self.offline_at = None

    def rawlink(self, *args, **kwargs):
        super(Event, self).rawlink(*args, **kwargs)
        if self.waiters == 1:
            self.manager.event_set_state(self.channel, True)

    def unlink(self, *args, **kwargs):
        super(Event, self).unlink(*args, **kwargs)
        if not self.waiters:
            self.manager.event_set_state(self.channel, False)
            self.offline_at = time()

    @property
    def waiters(self):
        return len(self._links)