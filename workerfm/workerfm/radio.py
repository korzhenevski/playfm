#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
from urlparse import urlparse, urljoin
from cStringIO import StringIO

from .errors import TooManyRedirects, ConnectionError, HttpError, InvalidMetaint, InvalidContentType


class RadioClient(object):
    def __init__(self, url, timeout=5, user_agent=None, **kwargs):
        self.url = url
        self.timeout = timeout
        if user_agent is None:
            user_agent = 'WinampMPEG/5.0'
        self.user_agent = user_agent
        self.headers = None

    def connect(self):
        url = urlparse(self.url)
        redirs = 0

        while True:
            if redirs > 5:
                raise TooManyRedirects()

            self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.stream.settimeout(self.timeout)

            try:
                self.stream.connect((url.hostname, url.port or 80))
            except socket.timeout:
                raise ConnectionError('timeout')
            except socket.error as exc:
                raise ConnectionError(unicode(exc))

            self.send_request(url.hostname, url.path)
            self.parse_headers()

            if self.status_code in (301, 302, 303, 307):
                location = self.headers.get('location')
                if not location:
                    raise HttpError('empty redirect')
                url = urlparse(urljoin(url.geturl(), location))
                redirs += 1
                continue
            elif self.status_code != 200:
                raise HttpError(self.status_code)

            self._validate_response()
            break

    def send_request(self, hostname, path):
        request = '\r\n'.join([
            'GET %s HTTP/1.0' % path,
            'Host: ' + hostname,
            'User-Agent: ' + self.user_agent,
            'Accept: */*',
            'Icy-Metadata: 1',
            '', ''
        ])
        self.stream.send(request)

    def parse_headers(self):
        self.status_code = 0
        data = self.read_stream(2048)
        if not data:
            return
        data = data.split('\r\n\r\n', 1)
        if not len(data) == 2:
            return
        headers, self.body_rest = data
        headers = headers.split('\r\n')
        self.status_code = int(headers[0].split(' ', 2)[1])
        headers = [header.split(':', 1) for header in headers[1:]]
        # lowercase/strip keys and values
        self.headers = dict([(name.strip().lower(), val.strip()) for name, val in headers])

    def read_stream(self, amt):
        s = StringIO()
        while amt > 0:
            if not self.stream:
                return
            chunk = self.stream.recv(min(amt, 1024 * 128))
            if not chunk:
                break
            s.write(chunk)
            amt -= len(chunk)
        return s.getvalue()

    def _validate_response(self):
        content_type = self.headers.get('content-type', '')
        if not (content_type.startswith('audio/') or content_type == 'application/octet-stream'):
            raise InvalidContentType()

        try:
            metaint = int(self.headers.get('icy-metaint'))
            if 1024 < metaint < 64 * 1024:
                self.metaint = metaint
            else:
                raise InvalidMetaint()
        except ValueError:
            raise InvalidMetaint()

    def read(self):
        # читаем первый чанк с учетом прочитанного контента в заголовках
        if self.body_rest:
            chunk_size = self.metaint - len(self.body_rest)
            self.body_rest = None
        else:
            chunk_size = self.metaint

        chunk = self.read_stream(chunk_size)
        metasize = self.read_stream(1)
        if metasize:
            metasize = ord(metasize) * 16
            meta = self.read_stream(metasize).strip("\x00")
        else:
            meta = None

        return chunk, meta

    def close(self):
        if self.stream:
            self.stream.shutdown(1)
            self.stream.close()
            self.stream = None