#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import errno
from time import time


class StripeWriter(object):
    def __init__(self, volume, stripe_size=256 * 1024 * 1024):
        self.volume = volume
        self.stripe = None
        self.stripe_index = 0
        self.stripe_size = stripe_size

    def write(self, data):
        if not self.stripe:
            return

        # stripe rotate
        if self.stripe_size and self.offset >= self.stripe_size:
            self.new_stripe()

        self.stripe.write(data)
        self.offset += len(data)

    def new_stripe(self):
        self.offset = 0
        self.stripe_index += 1

        name = str(int(round(time() * 10000)))
        self.name = '{}_{}'.format(name, self.stripe_index)

        # build scheme: /<volume_path>/<last_name_letter>/<last_2_name_letters>
        self.path = os.path.join(self.volume, name[-1:], name[-3:-1])
        self._makedir(self.path)
        self.stripe = open(os.path.join(self.path, name), 'a', buffering=0)

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
