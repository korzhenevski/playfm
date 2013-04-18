import json
import string
import urllib
import urllib2
from datetime import datetime
import logging

class TrackFactory(object):
    def __init__(self, lastfm_url, lastfm_api_key):
        self.lastfm_url = lastfm_url
        self.lastfm_api_key = lastfm_api_key

    def parse_stream_title(self, rawmeta):
        # extract StreamTitle='...';
        try:
            # add chardet
            rawmeta = rawmeta.decode('utf8')
            meta = dict([chunk.split('=', 1) for chunk in rawmeta.split(';') if '=' in chunk])
            meta = dict([(k.lower(), unicode(v).strip("'\"").strip()) for k, v in meta.iteritems()])
            return meta.get('streamtitle')
        except UnicodeDecodeError:
            return

    def build_track(self, stream_title):
        if not stream_title:
            return
        # normalize "Artist - Track"
        chunked_title = stream_title.split(' - ', 1)
        chunked_title = filter(None, map(string.strip, chunked_title))
        if not chunked_title:
            return
        track = {
            'title': string.join(chunked_title, ' - '),
            'rawtitle': stream_title,
            'artist': u'',
            'name': u'',
            'image_url': u'',
            'tags': [],
            'created_at': datetime.now(),
        }
        # if track without artist/name chunks (e.g. "Welcome to Radio"), skip last.fm lookup
        if len(chunked_title) < 2:
            logging.debug('skip last.fm lookup')
            return track
        track['artist'] = chunked_title[0]
        track['name'] = chunked_title[1]
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
                    images = dict([(image['size'], image['#text']) for image in album['image']])
                    image_url = images.get('medium', images.get('small'))
                    if image_url and 'noimage' not in image_url:
                        track['image_url'] = image_url
                    # tags aka "genres"
            if 'toptags' in lastfm_info and isinstance(lastfm_info['toptags'], dict):
                tags = lastfm_info['toptags'].get('tag', ())
                if isinstance(tags, dict):
                    tags = [tags['name']]
                else:
                    tags = [tag['name'] for tag in tags]
                track['tags'] = tags

        return track

    def lastfm_search(self, artist, trackname, timeout=1):
        url = self.lastfm_url + '?' + urllib.urlencode({
            'method': 'track.getinfo',
            'api_key': self.lastfm_api_key,
            'autocorrect': '1',
            'format': 'json'
        })
        url += '&artist=%s' % urllib.quote(artist.encode('utf8'))
        url += '&track=%s'  % urllib.quote(trackname.encode('utf8'))
        info = {}

        try:
            request = urllib2.Request(url, None, {'User-Agent': 'Mozilla/4.0 Compatible Browser'})
            client = urllib2.urlopen(request, timeout=timeout)
            info = json.loads(client.read())
        except Exception as e:
            print e

        if 'track' in info:
            return info['track']
        return None
