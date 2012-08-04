import gevent
from gevent import monkey
monkey.patch_all()
from gevent import socket
from urlparse import urlparse
from http_parser.parser import HttpParser
from gevent import Timeout
import sys
from pprint import pprint

class Radio(object):
    def __init__(self, url):
        self.url = urlparse(url)

    def connect(self):
        self.connected = False
        self.parser = HttpParser(kind=1)
        self.headers = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        error = None
        try:
            with Timeout(2):
                self.socket.connect((self.url.hostname, self.url.port or 80))
                self._http_request()
                status_code, self.headers = self._get_headers()
            if status_code == 200:
                error = self._validate_response()
            else:
                error = 'http error %s' % status_code
        except Exception, e:
            raise
            #error = str(e)
        return error

    def _http_request(self):
        request = '\r\n'.join([
            'GET %s HTTP/1.0' % self.url.path,
            'Host: %s' % self.url.hostname,
            'User-Agent: WinampMPEG/5.0',
            'Accept: */*',
            'Icy-Metadata: 1',
            '', ''
        ])
        status_done = False
        self.socket.send(request)

    def _get_headers(self):
        data = ''
        self.body_rest = ''
        while True:
            data += self.socket.recv(1024)
            if '\r\n\r\n' in data:
                headers_list, self.body_rest = data.split('\r\n\r\n')
                headers_list = headers_list.split('\r\n')
                status_code = int(headers_list[0].split(' ')[1])
                headers = dict([header.split(':', 1) for header in headers_list if ':' in header])
                headers = dict([(key.lower(), val) for key, val in headers.iteritems()])
                return status_code, headers
 
    def _get_headers2(self):
        status_done = False
        self.received = 0
        while True:
            data = self.socket.recv(1024)
            received = len(data)
            self.received += received
            # monkey patch non-RFC ICY status alike HTTP/1.0 
            if not status_done and received > 3:
                if data[0:3] == 'ICY':
                    data = data.replace('ICY', 'HTTP/1.0')
                status_done = True
            # add check received == parsed
            self.parser.execute(data, received)
            if self.parser.is_headers_complete():
                break
            gevent.sleep()
        headers = self.parser.get_headers()
        self.headers = dict([(k.lower(), v) for k, v in headers.items()])
 
    def _validate_response(self):
        content_type = self.headers.get('content-type')
        if not content_type:
            return 'no content type'
        if not content_type.startswith('audio/'):
            return 'invalid content-type %s' % content_type
        try:
            metaint = int(self.headers.get('icy-metaint'))
            if metaint > 64000:
                return 'metaint is too large'
            if metaint < 1024:
                return 'metaint is too small'
            self.metaint = metaint
        except ValueError, KeyError:
            return 'invalid metaint'

    def stream_info(self):
        readlen = self.metaint - len(self.body_rest)
        self.socket.recv(readlen)
        while True:
            infolen = ord(self.socket.recv(1)) * 16
            print 'infolen:', infolen
            if infolen:
                info = self.socket.recv(infolen)
                #yield info.strip("\x00")
            self.socket.recv(self.metaint)

url = sys.argv[1]
radio = Radio(url=url)
status = radio.connect()
pprint(radio.headers)
if status:
    print status
else:
    print radio.stream_info()
