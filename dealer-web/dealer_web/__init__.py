#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import pymongo
from flask import Flask, jsonify, request, abort, render_template
from spike_pb2 import Request

app = Flask(__name__)
app.jinja_env.variable_start_string = '{{{'
app.jinja_env.variable_end_string = '}}}'
app.jinja_env.block_start_string = '{{%'
app.jinja_env.block_end_string = '%}}'

db = pymongo.Connection(host='192.168.2.2')['playfm']

@app.route('/request', methods=['POST'])
def request_put():
    data = request.json
    if not data:
        abort(400)

    # проверка запроса
    req = Request()
    for name, val in data.iteritems():
        if hasattr(req, name):
            setattr(req, name, val)
    if not req.IsInitialized():
        abort(400)

    task_id = db.ids.find_and_modify({'_id': 'task'}, {'$inc': {'next': 1}}, new=True, upsert=True)['next']
    task_id = int(task_id)

    task = {
        '_id': task_id,
        'request': data,
        'consumer': data.get('consumer', 'playfm'),
        'status': 'queued',
        'queued_at': int(time.time()),
    }
    db.tasks.insert(task)

    return jsonify({'task': task})

@app.route('/tasks/')
@app.route('/tasks/<consumer>')
def consumer_tasks(consumer=None):
    where = {'consumer': consumer} if consumer else {}
    tasks = [task for task in db.tasks.find(where, fields={'result': 0})]
    return jsonify({'tasks': tasks})

@app.route('/tasks/<consumer>/<int:request_id>')
def request_result(consumer, request_id):
    task = db.tasks.find_one({'_id': request_id, 'consumer': consumer})
    if not task:
        return abort(404)
    return jsonify({'task': task})

@app.route('/')
def index():
    return render_template('index.html')


def main():
    return app.run(host='0.0.0.0', debug=True)

if __name__ == '__main__':
    main()