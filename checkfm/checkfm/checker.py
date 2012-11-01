import gevent
import logging
from time import time
from gevent.pool import Pool
from gevent.queue import Queue
from checkfm.client import RadioClient

class Checker(object):
    def __init__(self, db, interval, retries, timeout):
        self.db = db
        self.interval = interval
        self.retries = retries
        self.timeout = timeout
        self.results = Queue()
        self.threads = Pool()

    def run(self):
        gevent.joinall([
            gevent.spawn(self.select_streams),
            gevent.spawn(self.commit_results),
        ])

    def select_streams(self):
        logging.info('select streams...')
        while True:
            logging.debug('fetch streams checked %s secs ago', self.interval)
            streams = self.db.streams.find({
                'checked_at': {'$lt': int(time() - self.interval)},
                'perform_check': True
            }).limit(100)
            for stream in streams:
                logging.info('check stream %s: %s', stream['id'], stream['url'])
                self.threads.spawn(self.check_stream, stream['id'], stream['url'])
            gevent.sleep(10)

    def commit_results(self):
        logging.info('wait for results...')
        streams = self.db.streams
        for stream_id, result in self.results:
            checked_at = int(time())
            if result['error']:
                stream = streams.find_and_modify({'id': stream_id}, update={
                    '$set': {'check_error': result['error'], 'checked_at': checked_at},
                    '$inc': {'check_retries': 1}
                }, new=True)
                if stream['check_retries'] >= self.retries:
                    logging.info('stream %d offline', stream_id)
                    streams.update({'id': stream_id}, {'$set': {'is_online': False}})
                else:
                    logging.info('stream %d backoff', stream_id)
            else:
                stream = streams.find_and_modify({'id': stream_id}, {'$set': {
                    'bitrate': result['bitrate'],
                    'is_shoutcast': result['is_shoutcast'],
                    'is_online': True,
                    'check_error': '',
                    'check_retries': 0,
                    'checked_at': checked_at
                }})
                logging.info('stream %d online', stream_id)

        # update station online streams list
            update = {}
            key = '$pull' if result['error'] else '$addToSet'
            update[key] = {'online_streams': stream_id}
            self.db.stations.update({'id': stream['station_id']}, update)

    def check_stream(self, stream_id, url):
        try:
            client = RadioClient(url, timeout=self.timeout)
            info = client.get_info()
            self.results.put((stream_id, info))
        except Exception as exc:
            logging.exception(exc)