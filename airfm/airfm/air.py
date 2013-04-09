#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import ujson as json
from pymongo.connection import MongoClient
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from jinja2 import Environment, FileSystemLoader
from .manager import Manager

def jsonify(data=None, **kwargs):
    return Response(json.dumps(data or kwargs or {}), mimetype='application/json')

# добавить понятие метода и параметров метода
# comet.on('air/10432_32423', {wait: 25, uid: 10}, function(resp){
# })

class Comet(object):
    def __init__(self, config):
        self.mongo = MongoClient(host=config['mongo_host'], port=config['mongo_port'])
        self.manager = Manager()

        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        self.url_map = Map([
            Rule('/loader', endpoint='loader'),
            Rule('/air/<channel_name>', endpoint='air'),
        ])

    def on_air(self, request, channel_name):
        user_id = abs(request.args.get('uid', type=int, default=0))
        timeout = abs(request.args.get('wait', type=int, default=0))
        if timeout >= 60:
            timeout = 60

        channel = self.manager.get_channel(channel_name)
        channel.wait(timeout)

        return jsonify(air={'artist': 'Artist', 'name': 'Name'})

    def on_loader(self, request):
        return self.render_template('loader.html')

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

def create_app(mongo_host='127.0.0.1', mongo_port=27017):
    app = Comet({
        'mongo_host': mongo_host,
        'mongo_port': mongo_port,
    })
    return app
