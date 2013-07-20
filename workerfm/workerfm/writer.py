#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import errno
import logging
from zlib import crc32


class StripeWriter(object):
    def __init__(self, volume, name):
        self.offset = 0
        self.volume = volume
        self.stripe = None
        self.name = name

        self.new_stripe()

    def write(self, data):
        if not self.stripe:
            return

        self.stripe.write(data)
        self.offset += len(data)

    def get_full_path(self):
        name_hash = str(crc32(self.name) & 0xffffffff)
        return os.path.join(self.volume, name_hash[0], name_hash[:2], self.name)

    def new_stripe(self):
        self.offset = 0

        self.path = self.get_full_path()
        self._makedir(os.path.dirname(self.path))

        self.stripe = open(self.path, 'a', buffering=0)
        logging.info('new stripe %s', self.path)

    def close(self):
        self.path = None
        self.name = None
        if self.stripe:
            self.stripe.close()
            self.stripe = None

    def _makedir(self, path):
        if os.path.exists(path):
            return

        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise
