#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from time import time

class StripeWriter(object):
    def __init__(self, base, prefix=None, rotate_size=1024 * 1024 * 64, **kwargs):
        self.base = base
        self.prefix = prefix
        self.rotate_size = rotate_size
        self.stripe = None
        self.rotate_index = 0

    def open(self):
        self.rotate_index += 1
        self.written = 0

        stripe_id = str(int(round(time() * 1000)))
        self.name = '{}{}_{}'.format(self.prefix, stripe_id, self.rotate_index)
        # build scheme: base/<last_name_letter>/<last_2_name_letters>/name_with_prefix_and_rotate_index
        self.path = os.path.join(self.base, stripe_id[-1:], stripe_id[-3:-1], self.name)
        os.makedirs(os.path.dirname(self.path))

        self.stripe = open(self.path, 'a', buffering=0)

    def close(self):
        if self.stripe:
            self.path = None
            self.name = None
            self.stripe.close()
            self.stripe = None

    def write(self, data):
        if not self.stripe:
            self.open()
        self.stripe.write(data)
        self.written += len(data)
        # rotate, if exceed size
        if self.rotate_size and self.written >= self.rotate_size:
            self.open()