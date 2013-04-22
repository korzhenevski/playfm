#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import errno
from time import time
from bson.objectid import ObjectId


class StripeWriter(object):
    def __init__(self):
        self.stripe = None
        self.stripe_index = 0
        self.volume = None

    def configure(self, volume, stripe_size=None):
        self.volume = volume
        if stripe_size is None:
            # 256 Mb ~ 5 hours of 320 kbps stream
            stripe_size = 256 * 1024 * 1024
        self.stripe_size = stripe_size

    def new_stripe(self):
        self.stripe_index += 1
        self.offset = 0

        name = str(int(round(time() * 10000)))
        self.name = '{}_{}'.format(name, self.stripe_index)

        # build scheme: /<volume_path>/<last_name_letter>/<last_2_name_letters>
        self.path = os.path.join(self.volume, name[-1:], name[-3:-1])
        self._makedir(self.path)
        self.stripe = open(os.path.join(self.path, name), 'a', buffering=0)

    def _makedir(self, path):
        if os.path.exists(path):
            return
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass

    def close(self):
        if self.stripe:
            self.path = None
            self.name = None
            self.stripe.close()
            self.stripe = None

    def write(self, data):
        if not self.stripe:
            self.new_stripe()

        # stripe rotate, if exceed size
        if self.stripe_size and self.offset >= self.stripe_size:
            self.new_stripe()

        self.stripe.write(data)
        self.offset += len(data)
