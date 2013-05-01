#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import errno
from time import time
import logging


class StripeWriter(object):
    def __init__(self, volume, stripe_size=1024 * 1024 * 256):
        self.volume = volume
        self.stripe = None
        self.stripe_index = 0
        self.offset = 0
        self.stripe_size = stripe_size

    def write(self, data):
        if not self.stripe:
            return

        self.stripe.write(data)
        self.offset += len(data)

    def need_rotate(self):
        return self.stripe_size and self.offset >= self.stripe_size

    def new_stripe(self):
        self.offset = 0
        self.stripe_index += 1

        self.name = '{}{}'.format(self.stripe_index, int(round(time() * 10000)))[::-1]

        # build scheme: /<volume_path>/<last_name_letter>/<last_2_name_letters>
        self.path = os.path.join(self.volume, self.name[-1], self.name[-3:-1], self.name)
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
