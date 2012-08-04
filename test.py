__author__ = 'username'

import gevent
from gevent.monkey import patch_all
patch_all()
from gevent_zeromq import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect('tcp://127.0.0.1:10050')
socket.identity = 'worker'

while True:
    request = socket.send('test')
    print socket.recv()