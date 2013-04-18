#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from time import time


class StripeWriter(object):
    def __init__(self):
        self.stripe = None
        self.stripe_index = 0
        self.volume = None

    def configure(self, volume, stripe_size=None):
        self.volume = volume
        if stripe_size is None:
            # 64 Mb
            stripe_size = 1024 * 1024 * 64
        self.stripe_size = stripe_size

    def new_stripe(self):
        self.stripe_index += 1
        self.written = 0

        name = str(int(round(time() * 1000)))
        self.name = '{}_{}'.format(name, self.stripe_index)

        # build scheme: /<volume_path>/<last_name_letter>/<last_2_name_letters>/<name_with_rotate_index>
        self.path = os.path.join(self.volume, name[-1:], name[-3:-1], self.name)
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
            self.new_stripe()
        self.stripe.write(data)
        self.written += len(data)
        # stripe rotate, if exceed size
        if self.stripe_size and self.written >= self.stripe_size:
            self.new_stripe()

    def is_available(self):
        return self.volume