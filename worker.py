# -*- coding: utf-8 -*-
# какое замечательное слово worker :)

import gevent
from gevent.monkey import patch_all
patch_all()
from gevent import socket
from urlparse import urlparse, urljoin
from gevent.queue import Queue
from gevent.pool import Pool
from gevent_zeromq import zmq
import json

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

class StreamWorker(object):
    def __init__(self, job_id, url, parent):
        self.job_id = job_id
        self.url = url
        self.parent = parent
        self.error = None
        self.meta = None

    def run(self):
        gevent.joinall([
            gevent.spawn(self.trace),
            gevent.spawn(self.heatbeat)
        ])

    def trace(self, default_timeout=2, max_timeout=10):
        radio = Radio(self.url)
        timeout = default_timeout
        while True:
            self.error = None
            self.meta = None
            try:
                radio.connect()
                # reset after success connect
                timeout = default_timeout
                for meta in radio.stream_meta():
                    self.parent.job_status(self.job_id, 'meta', meta)
            except Exception as exc:
                self.parent.job_status(self.job_id, 'error', str(exc))
                # incremental timeout
                if timeout > max_timeout:
                    timeout = max_timeout
                else:
                    timeout = int(timeout * 1.5)
                gevent.sleep(timeout)

    def heatbeat(self):
        while True:
            self.parent.job_status(self.job_id, 'heartbeat')
            gevent.sleep(5)

class Worker(object):
    def __init__(self, manager_endpoint, events_endpoint):
        self.events = Queue()
        self.pool = Pool(size=1)
        self.jobs = {}
        self.manager_endpoint = manager_endpoint
        self.events_endpoint = events_endpoint
        self.context = zmq.Context()

    def worker(self):
        print 'worker'
        self.manager_socket = self.context.socket(zmq.REQ)
        self.manager_socket.connect(self.manager_endpoint)
        while True:
            print 'pool waiting...'
            self.pool.wait_available()
            self.manager_socket.send('ready')
            cmd, payload = self.manager_socket.recv_multipart()
            print 'cmd %s: %s' % (cmd, payload)
            if cmd == 'job':
                job = json.loads(payload)
                worker = StreamWorker(job['id'], url=job['url'], parent=self)
                self.jobs[job['id']] = self.pool.spawn(worker.run)
            elif cmd == 'wait':
                gevent.sleep(1)
            else:
                print 'worker invalid cmd: %s' % cmd
            gevent.sleep()

    def run(self):
        notifier = gevent.spawn(self.event_sender)
        worker = gevent.spawn(self.worker)
        gevent.joinall([notifier, worker])

    def event_sender(self):
        print 'event sender'
        self.events_socket = self.context.socket(zmq.REQ)
        self.events_socket.connect(self.events_endpoint)
        for job_id, payload in self.events:
            if job_id not in self.jobs:
                continue
            print 'notify manager, job %s: %s' % (job_id, payload)
            self.events_socket.send_multipart(['job_status', job_id, payload])
            reply = self.events_socket.recv()
            print 'event reply: %s' % reply
            # kill job, if manager reply 404 for status request
            if reply == '404':
                print 'got 404 status reply, kill job %s' % (job_id)
                self.jobs[job_id].kill()

    def job_status(self, job_id, msg_type, data=None):
        payload = json.dumps({
            'type': msg_type,
            'data': data
        })
        self.events.put([str(job_id), payload])


def inspect_stream(url):
    radio = Radio(url)
    try:
        status = radio.connect(timeout=10)
        if status is True:
            #pprint(radio.headers)
            #print '- metaint', radio.metaint
            for meta in radio.stream_meta():
                print '- ' + meta
                break
        else:
            print '-' + status
    except RuntimeError as e:
        pass
        #print url, str(e)
    except Exception as e:
        #print '- %s' % e
        return

"""
pool = Pool()
with open('./streams.txt') as fp:
    for url in fp:
        url = url.strip()
        worker = StreamWorker(url)
        pool.spawn(worker.run)

pool.join()
"""

if __name__ == '__main__':
    import sys
    worker = Worker(manager_endpoint='tcp://127.0.0.1:10050', events_endpoint='tcp://127.0.0.1:22005')
    worker.run()
    #from pprint import pprint
    #worker = StreamWorker(url=sys.argv[1])
    #worker.run()
    #trace_stream(sys.argv[1])