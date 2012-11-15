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
        #self.downloader = PlaylistDownloader(db=self.db)

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
            ts = int(time())
            if result['error']:
                stream = streams.find_and_modify({'id': stream_id}, {
                    '$set': {'check_error': result['error'], 'checked_at': ts},
                    '$inc': {'check_retries': 1}
                }, new=True)
                if stream['check_retries'] >= self.retries:
                    logging.info('stream %d offline', stream_id)
                    streams.update({'id': stream_id}, {'$set': {'is_online': False, 'error_at': ts}})
                else:
                    logging.info('stream %d backoff', stream_id)
            else:
                stream = streams.find_and_modify({'id': stream_id}, {'$set': {
                    'bitrate': result['bitrate'],
                    'is_shoutcast': result['is_shoutcast'],
                    'is_online': True,
                    'check_error': '',
                    'check_retries': 0,
                    'checked_at': ts,
                    'error_at': 0,
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

"""
class PlaylistDownloader(object):
    def __init__(self, db):
        self.interval = 86400
        self.db = db

    def run(self):
        while True:
            logging.info('download playlists...')
            where = {
                #'playlist_updated_at': {'$lt': int(time() - self.interval)},
                'playlist_updated_at': 0,
                'playlist': {'$not': {'$size': 0}, '$exists': True},
            }
            stations = self.db.stations.find(where, fields=['id','playlist'], sort=[('id', 1)]).limit(20)

            requests = []
            for station in stations:
                for playlist_url in station['playlist']:
                    print playlist_url
                    request = grequests.get(playlist_url, timeout=1, headers={'User-Agent': 'iTunes/9.1.1'})
                    request.station_id = station['id']
                    requests.append(request)

            for request in grequests_imap(requests, prefetch=False, size=20):
                if not request:
                    print 'failed'
                    continue
                station_id = request.station_id
                print request.response.request.url
                self.download_playlist(request.response, station_id)
                self.db.stations.update({'id': station_id}, {'$set': {'playlist_updated_at': int(time())}})

            gevent.sleep(0)

    def download_playlist(self, response, station_id):
        if not response.ok:
            logging.info(response.error)
            self.db.stations.update({'id': station_id}, {'$set':{'playlist_updated': False}})
            return False

        content_type = response.headers.get('content-type', '').split(';')[0].lower()
        if content_type not in ('application/pls+xml', 'audio/x-mpegurl', 'audio/x-scpls', 'text/plain', 'audio/scpls'):
            return False

        urls = self.extract_streams(response.content)
        self.update_station_streams(station_id, urls, playlist_url=response.request.url)
        self.db.stations.update({'id': station_id}, {'$set':{'playlist_updated': True}})

    def update_station_streams(self, station_id, urls, playlist_url):
        print '{} has {} streams'.format(station_id, len(urls))
        streams = self.db.streams
        streams.remove({'station_id': station_id, 'playlist_url': playlist_url})
        for url in urls:
            stream = dict(
                station_id=station_id,
                url=unicode(url),
                created_at=datetime.now(),
                checked_at=0,
                error_at=0,
                bitrate=0,
                is_online=False,
                playlist_url=unicode(playlist_url),
                perform_check=True,
                is_shoutcast=False)
            stream['id'] = self.db.object_ids.find_and_modify({'_id': 'streams'}, {'$inc': {'next': 1}}, new=True, upsert=True)['next']
            streams.insert(stream)

    def normalize_url(self, url):
        try:
            return urlnorm.norm(url)
        except urlnorm.InvalidUrl:
            print 'invalid url: ' + url
            pass
        return None

    def extract_streams(self, text):
        regex = r"(?im)^(file(\d+)=)?(http(.*?))$"
        urls = set([self.normalize_url(match.group(3).strip()) for match in re.finditer(regex, text)])
        return filter(None, urls)

def grequests_imap(requests, prefetch=True, size=2):
    ""Concurrently converts a generator object of Requests to
    a generator of Responses.

    :param requests: a generator of Request objects.
    :param prefetch: If False, the content will not be downloaded immediately.
    :param size: Specifies the number of requests to make at a time. default is 2
    ""

    pool = Pool(size)

    def send(r):
        r.send(prefetch)
        return r

    for r in pool.imap_unordered(send, requests):
        yield r

    pool.join()
"""