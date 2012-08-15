import gevent
import logging
from time import time
from gevent.pool import Pool
from gevent.queue import Queue
from checkfm.client import RadioClient

class Worker(object):
    def __init__(self, db, check_interval):
        self.db = db
        self.check_interval = check_interval
        self.result_queue = Queue()
        self.threads = Pool()

    def run(self):
        gevent.joinall([
            gevent.spawn(self.select_streams),
            gevent.spawn(self.commit_results),
        ])

    def select_streams(self):
        logging.info('select streams...')
        while True:
            logging.debug('fetch streams checked %s secs ago', self.check_interval)
            streams = self.db.streams.find({
                'checked_at': {'$lt': int(time() - self.check_interval)},
                'perform_check': True
            }).limit(100)
            for stream in streams:
                logging.info('check stream %s: %s', stream['id'], stream['url'])
                self.threads.spawn(self.check_stream, stream['id'], stream['url'])
            gevent.sleep(10)

    def commit_results(self):
        logging.info('wait for results...')
        for stream_id, result in self.result_queue:
            stream = {
                'check_error': result['error'],
                'checked_at': int(time()),
                'is_online': False,
            }
            if not result['error']:
                stream['bitrate'] = result['bitrate']
                stream['is_shoutcast'] = result['is_shoutcast']
                stream['is_online'] = True
                logging.debug('update stream %s - %s', stream_id, repr(stream))
            self.db.streams.update({'id': stream_id}, {'$set': stream})

    def check_stream(self, stream_id, url):
        try:
            client = RadioClient(url)
            info = client.get_info()
            self.result_queue.put((stream_id, info))
        except Exception as exc:
            logging.error(str(exc))