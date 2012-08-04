#!/usr/bin/python
# -*- coding: utf-8 -*-

"""WSGI server example"""
from gevent.pywsgi import WSGIServer
import gevent
from gevent.monkey import patch_all
patch_all()
from pprint import pprint 
import socket
import sys

def chunked_read(filepath, size):
    fp = open(filepath, 'r')
    while True:
        data = fp.read(size)
        if data and len(data) == size:
            yield data
        else:
            fp.seek(0)

def meta(info):
    info += "\x00" * (16 - (len(info) % 16))
    size = chr(len(info) / 16)
    print 'meta: %s' % len(info)
    return size + info

class IcyHandler(gevent.pywsgi.WSGIHandler):
    def start_response(self, status, headers, exc_info=None):
        if exc_info:
            try:
                if self.headers_sent:
                    # Re-raise original exception if headers sent
                    raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                # Avoid dangling circular ref
                exc_info = None
        self.code = int(status.split(' ', 1)[0])
        self.status = status
        self.response_headers = [(key.lower(), value) for key, value in headers]
        self.response_headers_list = [x[0] for x in self.response_headers]
        return self.write
    
    def write(self, data):
        towrite = []
        if not self.status:
            raise AssertionError("The application did not call start_response()")
        if not self.headers_sent:
            towrite.append('%s %s\r\n' % ('ICY', self.status))
            for header in self.response_headers:
                towrite.append('%s: %s\r\n' % header)
            towrite.append('\r\n')
            self.headers_sent = True
        if data:
            towrite.append(data)
        msg = ''.join(towrite)
        self.socket.sendall(msg)
        self.response_length += len(msg)

def application(env, start_response):
    metaint = 8192 
    headers = {
        'content-type': 'audio/mpeg',
        'icy-name': 'AH.FM - Leading Trance Radio',
        'icy-genre': 'Electronic Trance Dance',
        'icy-url': 'http//www.AH.FM',
        'icy-pub': '1',
        'icy-br': '192',
        'icy-metaint': str(metaint),
    }
    start_response('200 OK', headers.items())
    for chunk in chunked_read('./dump-radio', metaint):
        yield chunk
        #yield '0' * (len(chunk) - 1)
        yield meta("StreamTitle='title of the song';")
        gevent.sleep(0.1)

if __name__ == '__main__':
    print 'Serving on 8088...'
    WSGIServer(('', 8088), application, handler_class=IcyHandler).serve_forever()
