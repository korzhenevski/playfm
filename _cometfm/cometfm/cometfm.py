#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
        self.stats = {}

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
        info = self.redis.hgetall('onair:%s' % channel)
        # проверка наличия трека в избранном у пользователя
        #
        # список избранного может быть сколько-угодно большим,
        # лучше возвращать эту информацию отсюда
        if user_id and info.get('id'):
            cache_key = 'favorite_user_track:{}'.format(user_id)
            info['favorite'] = bool(self.redis.zscore(cache_key, info['id']))
        return info

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
            stats = {
                'channels': len(self.channels),
                'clients': 0
            }
            for channel, event in self.channels.iteritems():
                stats['clients'] += event.clients
                status = StreamStatus()
                status.type = StreamStatus.TOUCH
                status.station_id, status.stream_id = self.parse_channel(channel)
                status.clients = event.clients
                self.firehose.put(status)

            self.stats = stats
            gevent.sleep(5)

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

    @property
    def clients(self):
        return len(self._links)
