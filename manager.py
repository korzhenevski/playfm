# -*- coding: utf-8 -*-

import gevent
from gevent.monkey import patch_all
patch_all()
from gevent_zeromq import zmq
import json
import pymongo
from gevent.queue import Queue
from bson.objectid import ObjectId
import string
import urllib
import urllib2
from datetime import datetime
import redis
from pprint import pprint
class Stream(object):
    def __init__(self, object_id):
        self.object_id = object_id
        self.heartbeat_at = None
        self.job_id = None

class Manager(object):
    def __init__(self, endpoint, cometfm_endpoint, events_endpoint, updates_endpoint, db):
        self.endpoint = endpoint
        self.cometfm_endpoint = cometfm_endpoint
        self.events_endpoint = events_endpoint
        self.updates_endpoint = updates_endpoint
        self.context = zmq.Context()
        self.db = db
        self.streams = {}
        self.jobs = {}
        self.queue = set()
        self.job_id = 0
        self.tf_queue = Queue()
        self.redis = redis.Redis()

    def find_stream(self, stream_id):
        return self.db.streams.find_one({'_id': ObjectId(stream_id)})

    def subscribe_to_state_update(self):
        self.subsock = self.context.socket(zmq.SUB)
        self.subsock.setsockopt(zmq.SUBSCRIBE, 'STATE')
        self.subsock.connect(self.cometfm_endpoint)
        while True:
            topic, channel, is_active = self.subsock.recv_multipart()
            print '%s %s %s' % (topic, channel, is_active)
            station_id, stream_id = channel.split('_')
            if is_active == '1':
                self.put_stream(stream_id, channel)
            else:
                pass
                #self.remove_stream(stream_id)

    """
        Удаление потока
        - снимаем задачу
        - удаляем поток
        - удаляем из очереди обработки
    """
    def remove_stream(self, stream_id):
        print 'remove stream %s' % stream_id
        if stream_id in self.streams:
            stream = self.streams[stream_id]
            if stream['job_id']:
                self.cancel_job(stream['job_id'])
            self.streams.pop(stream_id)
            self.queue.remove(stream_id)

    """
        Добавление потока
        - добавляем поток
        - добавляем в очередь обработки
    """
    def put_stream(self, stream_id, channel):
        print 'put stream %s' % stream_id
        if stream_id not in self.streams:
            self.streams[stream_id] = {
                'id': stream_id,
                'hearbeat_at': None,
                'job_id': None,
                'channel': channel,
            }
            self.queue.add(stream_id)

    """
        Снятие задачи
        - удаляем задачу
        - обнуляем идентификатор задачи и время серцебиения в потоке
    """
    def cancel_job(self, job_id):
        print 'cancel job %s' % job_id
        if job_id in self.jobs:
            stream_id = self.jobs.pop(job_id)
            self.streams[stream_id].update({
                'hearbeat_at': None,
                'job_id': None
            })

    def get_job_for_worker(self, worker_id):
        if not self.queue:
            return
        stream_id = self.queue.pop()
        stream = self.find_stream(stream_id)
        if not stream:
            return
        self.job_id += 1
        job_id = str(self.job_id)
        self.jobs[job_id] = stream_id
        return {
            'id': job_id,
            #'url': stream['url']
            'url': 'http://ru.ah.fm/'
        }

    def run(self):
        gevent.joinall([
            gevent.spawn(self.manager),
            gevent.spawn(self.event_receiver),
            gevent.spawn(self.subscribe_to_state_update)
        ])

    def manager(self):
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind(self.endpoint)
        while True:
            worker_id, cmd, payload = self.recv_request(self.socket)
            if cmd == 'ready':
                job = self.get_job_for_worker(worker_id)
                if job:
                    job = json.dumps(job)
                    self.socket.send_multipart([worker_id, '', 'job', job])
                else:
                    self.socket.send_multipart([worker_id, '', 'wait', ''])
            else:
                print 'invalid cmd'
            gevent.sleep(0)

    def recv_request(self, sock):
        request = sock.recv_multipart()
        worker_id = request[0]
        payload = request[2:]
        cmd = payload[0]
        return worker_id, cmd, payload

    def event_receiver(self):
        self.events_socket = self.context.socket(zmq.ROUTER)
        self.events_socket.bind(self.events_endpoint)
        while True:
            worker_id, cmd, payload = self.recv_request(self.events_socket)
            if cmd != 'job_status':
                print 'invalid event_recv cmd'
                continue
            status = json.loads(payload[2])
            if self.process_job_status(payload[1], status_type=status['type'], data=status['data']):
                reply = '200'
            else:
                reply = '404'
            self.events_socket.send_multipart([worker_id, '', reply])
            gevent.sleep(0)

    def process_job_status(self, job_id, status_type, data):
        print 'got job %s, %s: %s' % (job_id, status_type, data)
        if job_id not in self.jobs:
            return False
        if status_type == 'meta':
            channel = self.streams[self.jobs[job_id]]['channel']
            self.tf_queue.put((channel, unicode(data)))

    def track_factory_worker(self):
        updates = self.context.socket(zmq.PUB)
        updates.bind(self.updates_endpoint)
        print self.updates_endpoint
        # wait for subs connect
        gevent.sleep(1)
        for channel, rawmeta in self.tf_queue:
            track = self.track_factory(rawmeta)
            if track:
                pprint(track)
                self.update_onair(channel, track)
                updates.send_multipart([channel, ''])

    def track_factory(self, rawmeta):
        # from StreamTitle=''; to dict
        try:
            # add chardet
            rawmeta = rawmeta.decode('utf8')
        except UnicodeDecodeError:
            return
        meta = dict([chunk.split('=') for chunk in rawmeta.split(';') if '=' in chunk])
        meta = dict([(k.lower(), unicode(v).strip("'\"").strip()) for k, v in meta.iteritems()])
        if not meta.get('streamtitle'):
            return
        # normalize "Artist - Track"
        stream_title = meta['streamtitle'].split(' - ', 1)
        stream_title = map(string.strip, stream_title)
        if not stream_title:
            return
        track = {
            'title': string.join(stream_title, ' - '),
            'rawtitle': meta['streamtitle'],
            'created_at': datetime.now(),
            'artist': u'',
            'name': u'',
            'image_url': u'',
            'tags': [],
        }
        if len(stream_title) == 2:
            track['artist'] = stream_title[0]
            track['name'] = stream_title[1]
            # last.fm lookup track.getInfo
            lastfm_info = self.lastfm_search(track['artist'], track['name'])
            if lastfm_info:
                track['lastfm_info'] = lastfm_info
                # normalize artist/trackname
                track['artist'] = lastfm_info.get('artist', {}).get('name', track['artist'])
                track['name'] = lastfm_info.get('name', track['name'])
                # get album cover, first size
                if 'album' in lastfm_info:
                    album = lastfm_info['album']
                    if album.get('image'):
                        track['image_url'] = album['image'][0].get('#text', '')
                # tags aka "genres"
                if 'toptags' in lastfm_info and isinstance(lastfm_info['toptags'], dict):
                    tags = lastfm_info['toptags'].get('tag', ())
                    if isinstance(tags, dict):
                        tags = [tags['name']]
                    else:
                        tags = [tag['name'] for tag in tags]
                    track['tags'] = tags

        track_id = self.db.tracks.insert(track)
        track['id'] = str(track_id)
        return track

    def update_onair(self, channel, track):
        # and build short onair track info
        onair_fields = ('id', 'title', 'artist', 'name', 'image_cover')
        onair = dict([(key, val) for key, val in track.iteritems() if key in onair_fields])
        # avoid duplicate
        # if onair['artist'] and onair['name']:
        #    onair.pop('title')
        self.redis.hmset('channel:%s' % channel, onair)

    def lastfm_search(self, artist, trackname, timeout=1):
        url = 'http://lastfm-proxy01.afm.fm/2.0/?'
        url += urllib.urlencode({
            'method': 'track.getinfo',
            'api_key': 'b25b959554ed76058ac220b7b2e0a026',
            'autocorrect': '1',
            'format': 'json'
        })
        url += '&artist=%s' % urllib.quote(artist.encode('utf8'))
        url += '&track=%s'  % urllib.quote(trackname.encode('utf8'))
        info = None

        try:
            request = urllib2.Request(url, None, {'User-Agent': 'Mozilla/4.0 Compatible Browser'})
            client = urllib2.urlopen(request, timeout=timeout)
            info = json.loads(client.read())
        except Exception as e:
            print e

        if 'track' in info:
            return info['track']
        return None

def main():
    manager = Manager(
        endpoint='tcp://*:10050',
        cometfm_endpoint='tcp://127.0.0.1:22002',
        events_endpoint='tcp://127.0.0.1:22005',
        updates_endpoint='tcp://127.0.0.1:22001',
        db=pymongo.Connection()['againfm'])
    #manager.run()
    channel = '5015c8861d41c85c0e8ec28f_5015c8861d41c85c0e8ec290'
    un = u'Дискотека Авария - суровый рэп'
    manager.tf_queue.put((channel, "StreamTitle='%s';StreamUrl='';" % un.encode('utf8')))
    manager.track_factory_worker()

if __name__ == '__main__':
    main()