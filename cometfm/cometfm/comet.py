#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import gevent
from redis import Redis, RedisError
import ujson as json
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from jinja2 import Environment, FileSystemLoader
from time import time
import psutil

from .manager import Manager
from .utils import retry_on_exceptions


def jsonify(data=None, **kwargs):
    return Response(json.dumps(data or kwargs or {}), mimetype='application/json')


def get_ts():
    return int(time())


class Comet(object):
    def __init__(self, config):
        self.redis = Redis(host=config['redis_host'], db=config['redis_db'])
        self.manager = Manager()

        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        self.url_map = Map([
            Rule('/loader', endpoint='loader'),
            Rule('/onair/<int:radio_id>', endpoint='air'),
            Rule('/stats', endpoint='stats'),
        ])

        self.process = psutil.Process(os.getpid())

    def on_loader(self, request):
        return self.render_template('loader.html')

    def on_air(self, request, radio_id):
        if radio_id >= 10 ** 9:
            return self.error_404()

        # validate channel_name
        timeout = abs(request.args.get('wait', type=int, default=0))
        if timeout >= 60:
            timeout = 60

        if timeout:
            channel = self.manager.get_channel(radio_id)
            channel.wait(timeout)

        try:
            user_id = abs(request.args.get('uid', type=int, default=0))
            info = self.get_onair(radio_id)

            if user_id and info.get('id'):
                cache_key = 'user:{}:onair_likes'.format(user_id)
                info['liked'] = bool(self.redis.zscore(cache_key, info['id']))
            return jsonify(info=info)
        except RedisError:
            return Response('', status=503, mimetype='application/json')

    def on_stats(self, request):
        process = {
            'cpu_percent': self.process.get_cpu_percent(),
            'memory_percent': self.process.get_memory_percent(),
        }
        return jsonify({'stats': {
            'channels': len(self.manager.channels),
            'process': process
        }})

    @retry_on_exceptions([RedisError])
    def get_onair(self, radio_id):
        return self.redis.hgetall('radio:{}:onair'.format(radio_id))

    @retry_on_exceptions([RedisError])
    def watch_for_updates(self):
        pubsub = self.redis.pubsub()
        pubsub.psubscribe('radio:*:onair_updates')

        for update in pubsub.listen():
            channel = update['channel']
            try:
                radio_id = int(channel.split(':')[-2])
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

    def service_visit(self):
        while True:
            self.manager.drop_offline_channels()
            gevent.sleep(1)



def create_app(redis_host='127.0.0.1', redis_db=0):
    app = Comet({
        'redis_host': redis_host,
        'redis_db': redis_db
    })
    return app
