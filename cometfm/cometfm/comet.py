#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import gevent
import psutil
import ujson as json
import logging
from redis import Redis, RedisError
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from jinja2 import Environment, FileSystemLoader

from .manager import Manager
from .utils import retry_on_exceptions


def jsonify(data=None, **kwargs):
    return Response(json.dumps(data or kwargs or {}), mimetype='application/json')


class Comet(object):
    def __init__(self, config):
        self.redis = Redis(host=config['redis_host'], db=config['redis_db'])
        self.manager = Manager()

        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        self.url_map = Map([
            Rule('/', endpoint='frame'),
            Rule('/stats', endpoint='stats'),
            Rule('/onair/<int:radio_id>', endpoint='air'),
        ])

        self.process = psutil.Process(os.getpid())

    def on_frame(self, request):
        return self.render_template('frame.html')

    def on_stats(self, request):
        total_clients = 0
        clients = {}
        for name, channel in self.manager.channels.iteritems():
            clients[name] = channel.clients_count
            total_clients += channel.clients_count

        return jsonify({
            'realtime': {
                'channels': len(self.manager.channels),
                'clients': clients,
                'total_clients': total_clients,
            },
            'process': {
                'cpu_percent': self.process.get_cpu_percent(),
                'memory_percent': self.process.get_memory_percent(),
            }
        })

    def on_air(self, request, radio_id):
        if radio_id >= 10 ** 9:
            return self.error_404()

        # validate channel_name
        timeout = abs(request.args.get('wait', type=int, default=0))
        if timeout >= 60:
            timeout = 60

        # first request without wait
        request_counter = request.headers.get('x-counter', type=int, default=0)
        if timeout and request_counter != 1:
            channel = self.manager.get_channel(radio_id)
            channel.wait(timeout)

        try:
            user_id = abs(request.args.get('uid', type=int, default=0))
            air = self.get_onair(radio_id)

            if user_id and air.get('id'):
                cache_key = 'user:{}:onair_likes'.format(user_id)
                air['liked'] = bool(self.redis.zscore(cache_key, air['id']))

            return jsonify(onair=air)
        except RedisError:
            return Response('', status=503, mimetype='application/json')

    @retry_on_exceptions([RedisError])
    def get_onair(self, radio_id):
        # TODO: add LRU caching
        return self.redis.hgetall('radio:{}:onair'.format(radio_id))

    @retry_on_exceptions([RedisError])
    def watch_for_updates(self):
        pubsub = self.redis.pubsub()
        pubsub.psubscribe('radio:*:onair_updates')

        for update in pubsub.listen():
            channel = update['channel']
            try:
                radio_id = int(channel.split(':')[-2])
                logging.info('update channel %s', radio_id)
                self.manager.wakeup_channel(radio_id)
            except ValueError:
                pass

    def error_404(self):
        return Response('404', mimetype='text/plain', status=404)

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html')

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except NotFound:
            return self.error_404()
        except HTTPException, e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    @retry_on_exceptions([RedisError])
    def update_stats(self):
        # TODO: add zset expire
        for name, channel in self.manager.channels.iteritems():
            self.redis.zadd('radio:clients', name, channel.clients_count)

    def service_visit(self):
        while True:
            self.manager.drop_offline_channels()
            self.update_stats()
            gevent.sleep(1)


def create_app(redis_host='127.0.0.1', redis_db=0):
    app = Comet({
        'redis_host': redis_host,
        'redis_db': redis_db
    })
    return app