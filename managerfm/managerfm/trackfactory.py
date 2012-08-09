import json
import string
import urllib
import urllib2
from datetime import datetime

class TrackFactory(object):
    def __init__(self, lastfm_url, lastfm_api_key):
        self.lastfm_url = lastfm_url
        self.lastfm_api_key = lastfm_api_key

    def build_track_from_stream_title(self, rawmeta):
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
            'artist': u'',
            'name': u'',
            'image_url': u'',
            'tags': [],
            'created_at': datetime.now(),
            }
        # if track without artist/name chunks (e.g. "Welcome to Radio"), skip last.fm lookup
        if len(stream_title) != 2:
            return track
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
