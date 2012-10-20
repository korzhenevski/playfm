import re
import urllib2
import socket
from checkfm import icyhttp
from time import time
from urlparse import urlparse

class RadioClient:
    _client = None

    def __init__(self, url, timeout=5):
        self.timeout = timeout
        self.url = urlparse(url)

    def get_info(self):
        info = dict(
            error='',
            is_shoutcast=False,
            time=time(),
            bitrate=0)

        try:
            req = urllib2.Request(self.url.geturl(), None, {
                # add robot description page
                # 'User-Agent': 'Mozilla/5.0 (compatible; A.FM; http://afm.fm/bot.html)',
                'User-Agent': 'Mozilla/5.0 (compatible; A.FM)',
                'Icy-Metadata': '1'})
            self._client = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as exc:
            info['error'] = 'HTTP Error: %s' % exc.code
        except urllib2.URLError as exc:
            if isinstance(exc.reason, socket.timeout):
                info['error'] = 'Request timeout (%d secs.)' % self.timeout
            else:
                info['error'] = 'URL Error: %s' % exc.reason
        except Exception as exc:
            info['error'] = 'Error: %s' % exc
        finally:
            info['time'] = '%.4f' % (time() - info['time'])

        if info['error']:
            return info

        headers = dict(self._client.info().items())
        content_type = headers.get('content-type', '')
        metaint = int(headers.get('icy-metaint', 0))

        if content_type in ('audio/mpeg', 'application/octet-stream'):
            if not metaint:
                info['error'] = 'Empty metaint'
            info['bitrate'] = self._get_bitrate(headers)
        elif content_type == 'text/html':
            page_content = self._client.read(8096)
            if 'SHOUTcast Administrator' in page_content:
                # Bitrate is important for stream selection,
                # extract value from Shoutcast Info HTML.
                bitrate_match = re.search(r"at (\d+) kbps", page_content, re.IGNORECASE)
                if bitrate_match:
                    info['bitrate'] = int(bitrate_match.group(1))
                info['is_shoutcast'] = True
            else:
                info['error'] = 'Invalid content type: text/html'
        else:
            info['error'] = 'Invalid content type: %s' % content_type

        self._disconnect()
        return info

    def _get_bitrate(self, headers):
        bitrate = 0
        for br_field in ('ice-bitrate', 'icy-br', 'x-audiocast-bitrate'):
            if br_field in headers:
                bitrate = headers.get(br_field)
        if bitrate and bitrate.isdigit():
            bitrate = int(bitrate)
        else:
            bitrate = 0
        return bitrate

    def _disconnect(self):
        if self._client:
            self._client.close()