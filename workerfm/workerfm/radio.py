# -*- coding: utf-8 -*-

import socket
from urlparse import urlparse, urljoin

class Radio(object):
    def __init__(self, url):
        self.url = urlparse(url)

    def connect(self, timeout=4):
        url = self.url
        redirs = 0
        try:
            while True:
                if redirs > 5:
                    raise RuntimeError('too many redirects')
                    #print url.geturl()
                self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.stream.settimeout(timeout)
                self.stream.connect((url.hostname, url.port or 80))
                self._send_request(url.hostname, url.path)
                self._parse_headers()
                if self.status_code in (301, 302, 303, 307):
                    location = self.headers.get('location')
                    if location:
                        url = urlparse(urljoin(url.geturl(), location))
                        redirs += 1
                        continue
                    else:
                        raise RuntimeError('redirect without location')
                elif self.status_code != 200:
                    raise RuntimeError('http %s' % self.status_code)
                self._validate_response()
                return True
        except Exception as e:
            raise

    def stream_meta(self):
        # первый чанк данных читаем за вычетом уже прочитанного тела
        chunk_size = self.metaint - len(self.body_rest)
        self.body_rest = ''
        while True:
            self.read_stream(chunk_size)
            size = ord(self.read_stream(1)) * 16
            if size:
                meta = self.read_stream(size)
                yield meta.strip("\x00")
            chunk_size = self.metaint

    def _send_request(self, hostname, path):
        request = [
            'GET %s HTTP/1.0' % path,
            'Host: %s' % hostname,
            'User-Agent: WinampMPEG/5.0',
            'Accept: */*',
            'Icy-Metadata: 1',
            '', ''
        ]
        request = '\r\n'.join(request)
        self.stream.send(request)

    def read_stream(self, amt):
        s = []
        while amt > 0:
            chunk = self.stream.recv(min(amt, 1024 * 1024))
            if not chunk:
                break
            s.append(chunk)
            amt -= len(chunk)
        return ''.join(s)

    def _validate_response(self):
        content_type = self.headers.get('content-type')
        if not content_type:
            raise RuntimeError('no content type')
        if not content_type.startswith('audio/'):
            raise RuntimeError('invalid content-type %s' % content_type)
        try:
            metaint = int(self.headers.get('icy-metaint'))
            if metaint > 64 * 1024:
                raise RuntimeError('metaint %s is too large' % metaint)
            if metaint < 1000:
                raise RuntimeError('metaint %s is too small' % metaint)
            self.metaint = metaint
        except ValueError, KeyError:
            raise RuntimeError('invalid metaint')

    def _parse_headers(self):
        data = ''
        while '\r\n\r\n' not in data:
            data += self.read_stream(512)
        data = data.split('\r\n\r\n')
        headers, self.body_rest = data
        headers = headers.split('\r\n')
        self.status_code = int(headers[0].split(' ', 2)[1])
        headers = [header.split(':', 1) for header in headers[1:]]
        # lowercase/strip keys and values
        self.headers = dict([(name.strip().lower(), val.strip()) for name, val in headers])

