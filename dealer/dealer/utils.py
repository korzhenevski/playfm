#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import gevent_zeromq as zmq
import logging
import google.protobuf.message
from binascii import hexlify, unhexlify

def pb_safe_decode(klass, raw):
    """
    Декодирование Protobuf данных с логированием ошибок
    """
    try:
        return klass.FromString(raw)
    except google.protobuf.message.DecodeError:
        logging.exception('Safe decode error')


class RouterSocket(object):
    def __init__(self, context, endpoint):
        self.sock = context.socket(zmq.ROUTER)
        self.sock.bind(endpoint)

    def reader(self, protobuf_class=None):
        """
        Итератор для чтения Protobuf сообщений
        """
        while self.sock:
            msg = self.sock.recv_multipart()
            # насколько важна эта проверка?
            if len(msg) < 3:
                continue

            message = msg[2]

            if protobuf_class:
                message = pb_safe_decode(protobuf_class, message)

            if not message:
                continue

            yield hexlify(msg[0]), message

            # даем другим задачам поработать
            gevent.sleep()

    def send(self, client_id, message):
        self.sock.send_multipart([unhexlify(client_id), '', message.SerializeToString()])

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

