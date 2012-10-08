#!/usr/bin/env python

import gevent
import logging
from gevent.event import Event as GeventEvent
from gevent_zeromq import zmq
from gevent.queue import Queue
from time import time
from rvlib import pb_safe_parse, pb_dump, OnairUpdate, StreamStatus

class Server(object):
    OFFLINE_DEADLINE = 60

    def __init__(self, redis, endpoint, onair_ttl):
        self.ctx = zmq.Context()
        self.channels = {}
        self.redis = redis
        self.endpoint = endpoint
        self.onair_ttl = onair_ttl
        self.firehose = Queue()

    def get_channel(self, name):
        if name not in self.channels:
            self.channels[name] = Event(manager=self, channel=name)
        return self.channels.get(name)

    def get_channel_name(self, station_id, stream_id):
        return '%s_%s' % (station_id, stream_id)

    def parse_channel(self, channel):
        channel = channel.split('_', 1)
        return map(int, channel)

    def event_set_state(self, channel, state, clients):
        status = StreamStatus()
        status.type = StreamStatus.ONLINE if state else StreamStatus.OFFLINE
        status.station_id, status.stream_id = self.parse_channel(channel)
        status.clients = clients
        self.firehose.put(status)

    def wakeup_channel(self, name):
        channel = self.get_channel(name)
        channel.set()
        channel.clear()

    def run(self):
        gevent.spawn(self.watch_onair_updates)
        gevent.spawn(self.activity_publisher)
        gevent.spawn(self.cleanup_offline_channels)
        gevent.spawn(self.firehose_hydrant)

    def cleanup_offline_channels(self):
        while True:
            current_time = time()
            channels = set()
            for channel, event in self.channels.iteritems():
                if event.clients == 0 and current_time - event.last_online_at >= self.OFFLINE_DEADLINE:
                    channels.add(channel)
            for channel in channels:
                self.channels.pop(channel)
            gevent.sleep(60)

    def get_info(self, station_id, stream_id, user_id, timeout):
        channel = self.get_channel_name(station_id, stream_id)
        if timeout is not None:
            self.get_channel(channel).wait(timeout)
        data = self.redis.hgetall('onair:%s' % channel)
        if user_id and data.get('id'):
            favs = UserFavorites(user_id=user_id, redis=self.redis)
            data['favorite'] = favs.exists('track', data['id'])
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
            onair_key = 'onair:%s' % channel
            self.redis.hmset(onair_key, cache_track)
            self.redis.expire(onair_key, self.onair_ttl)
            self.wakeup_channel(channel)

            gevent.sleep()


    def activity_publisher(self):
        while True:
            for channel, event in self.channels.iteritems():
                status = StreamStatus()
                status.type = StreamStatus.TOUCH
                status.station_id, status.stream_id = self.parse_channel(channel)
                status.clients = event.clients
                self.firehose.put(status)
            gevent.sleep(10)

    def firehose_hydrant(self):
        sock = self.ctx.socket(zmq.PUB)
        sock.bind(self.endpoint['firehose'])
        for message in self.firehose:
            logging.debug('stream status - %s', pb_dump(message))
            sock.send_multipart(['STATUS', message.SerializeToString()])

class Event(GeventEvent):
    def __init__(self, manager, channel, *args, **kwargs):
        super(Event, self).__init__(*args, **kwargs)
        self.manager = manager
        self.channel = channel
        self.last_online_at = time()

    def rawlink(self, *args, **kwargs):
        super(Event, self).rawlink(*args, **kwargs)
        self.last_online_at = time()
        if self.clients == 1:
            self.manager.event_set_state(self.channel, state=True, clients=self.clients)

    """
    def unlink(self, *args, **kwargs):
        super(Event, self).unlink(*args, **kwargs)
        if not self.clients:
            self.manager.event_set_state(self.channel, state=False, clients=self.clients)
    """

    @property
    def clients(self):
        return len(self._links)

class UserFavorites(object):
    def __init__(self, user_id, redis):
        self.redis = redis
        self.user_id = user_id

    def add(self, object_type, object_id):
        self.redis.zadd(self.object_key(object_type), object_id, self.get_ts())

    def exists(self, object_type, object_id):
        score = self.redis.zscore(self.object_key(object_type), object_id)
        return bool(score)

    def remove(self, object_type, object_id):
        self.redis.zrem(self.object_key(object_type), object_id)

    def toggle(self, object_type, object_id):
        exists = self.exists(object_type, object_id)
        if exists:
            self.remove(object_type, object_id)
        else:
            self.add(object_type, object_id)
        return not exists

    def object_key(self, object_type):
        return 'favorite_user_{}:{}'.format(object_type, self.user_id)

    def get_ts(self):
        return int(time.time())