#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import logging

from time import time
from gevent.pool import Pool
from gevent.queue import Queue
from checkfm.client import RadioClient

class Checker(object):
    def __init__(self, db, interval, retries, timeout, threads):
        self.db = db
        self.interval = interval
        self.retries = retries
        self.timeout = timeout
        self.results = Queue()
        self.threads = threads
        self.queue = Queue(self.threads)

    def run(self):
        pool = Pool()
        pool.spawn(self.producer)
        pool.spawn(self.commit_results)
        pool.spawn(self.update_station_status)
        for i in xrange(self.threads):
            pool.spawn(self.worker)
        pool.join()

    def update_station_status(self):
        while True:
            logging.info('update stations status')
            # радио без потоков лежащее более 12 часов - офлайн
            deadline = int(time() - 43200)
            self.db.stations.update({
                'online_at': {'$lte': deadline},
                'streams': {'$size': 0}
            }, {'$set': {'status': 0}}, multi=True)
            # радио без потоков лежащее менее 12 часов - просто помечаем как лежащее
            self.db.stations.update({
                'online_at': {'$gt': deadline},
                'streams': {'$size': 0}
            }, {'$set': {'status': 2}}, multi=True)
            # радио с потоками - онлайн
            self.db.stations.update({
                'streams': {'$exists': True, '$not': {'$size': 0}}
            }, {'$set': {'status': 1}}, multi=True)
            gevent.sleep(30)

    def producer(self):
        while True:
            checked_at = int(time() - self.interval)
            logging.debug('fetch streams')
            streams = self.db.streams.find({'checked_at': {'$lt': checked_at}, 'deleted_at': 0}, fields=['id','url'])
            for stream in streams:
                logging.info('check stream %s: %s', stream['id'], stream['url'])
                self.queue.put(stream)
            else:
                gevent.sleep(1)

    def worker(self):
        while True:
            stream = self.queue.get()
            try:
                client = RadioClient(stream['url'], timeout=self.timeout)
                self.results.put((stream['id'], client.request()))
            except Exception as exc:
                logging.exception(exc)
            gevent.sleep()

    def commit_results(self):
        logging.info('wait for results...')
        streams = self.db.streams
        for stream_id, result in self.results:
            ts = int(time())
            if result['error']:
                stream = streams.find_and_modify({'id': stream_id}, {
                    '$set': {
                        'error': result['error'],
                        'content_type': result['content_type'],
                        'checked_at': ts,
                        'error_at': ts,
                        'check_time': result['time'],
                    },
                    '$inc': {'check_retries': 1}
                }, new=True)

                if stream['check_retries'] >= self.retries:
                    logging.debug('stream %d offline', stream_id)
                    streams.update({'id': stream_id}, {'$set': {'is_online': False}})
                else:
                    logging.debug('stream %d backoff', stream_id)
            else:
                stream = streams.find_and_modify({'id': stream_id}, {
                    '$set': {
                        'bitrate': result['bitrate'],
                        'is_shoutcast': result['is_shoutcast'],
                        'is_online': True,
                        'content_type': result['content_type'],
                        'check_retries': 0,
                        'check_time': result['time'],
                        'checked_at': ts,
                        'error': '',
                        'error_at': 0,
                    }
                })
                logging.debug('stream %d online', stream_id)

            # update station streams
            update = {}
            key = '$pull' if result['error'] else '$addToSet'
            update[key] = {'streams': stream_id}
            update['$set'] = {'online_at': ts}
            self.db.stations.update({'id': stream['station_id']}, update)
