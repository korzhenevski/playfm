#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import requests
import logging

requests_log = logging.getLogger('requests')
requests_log.setLevel(logging.WARNING)


class Ester(object):
    def __init__(self, manager):
        self.manager = manager

    def scheduler(self):
        while True:
            resp = requests.get('http://127.0.0.1:6000/stats?clients=1')
            stats = resp.json()['stats']
            for radio_id, clients in stats.iteritems():
                task = self.manager.put_radio(radio_id)
                logging.info('put radio %s (clients: %s) - task_id: %s', radio_id, clients, task['_id'])
            gevent.sleep(1)