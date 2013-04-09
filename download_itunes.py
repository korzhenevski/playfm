#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import gevent.monkey
gevent.monkey.patch_all()

import pymongo


from geventhttpclient import HTTPClient, URL
from geventhttpclient._parser import HTTPParseError
from gevent.pool import Pool
from gevent.queue import Queue
from gevent import Timeout

db = pymongo.Connection(host='192.168.2.2', use_greenlets=True)['againfm']
db_radio = db['radio']

pool = Pool(size=15)

results = Queue()

def results_reader():
    for object_id, fetched_data in results:
        print fetched_data
        db_radio.update({'_id': object_id}, {'$set': {'playlist_fetch': fetched_data}})

def download_url(url, object_id):
    url = URL(url)
    http = HTTPClient.from_url(url, disable_ipv6=True)

    while True:
        try:
            response = http.get(url.request_uri)
            headers = dict(response.headers)

            if response.status_code in (301, 302, 305, 309):
                loc = headers.get('location')
                response = http.get(URL(url))
        except HTTPParseError:
            print 'shoutcast stream'
        finally:
            break


    if response.status_code != 200:
        print 'bad status code: {}'.format(response.status_code)
        return

    ct = headers.get('content-type', '').split(';')[0].strip()

    if ct not in ('audio/x-scpls', 'audio/x-mpegurl', 'text/html', 'text/plain', 'application/pls+xml', 'audio/text'):
        print 'bad content type: ' + ct
        return

    #print '{}: {} - {}'.format(response.status_code, ct, url)
    content = None
    with Timeout(5, None):
        content = response.read()

    if content is None:
        print '{} - empty content'.format(url)
        return

    results.put_nowait((object_id, {'headers': headers, 'content': content}))


#download_url('http://hu.ah.fm:9000/', None)

gevent.spawn(results_reader)

for radio in db_radio.find({'playlist_fetch': {'$exists': False}}):
    url = radio['playlist']
    if '.pls' in url or '.m3u' in url:
        pool.spawn(download_url, url, radio['_id'])
