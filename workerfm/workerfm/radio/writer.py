#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from time import time

class StripeWriter(object):
    def __init__(self, base, stripe_id, rotate_size=1024 * 1024 * 64, **kwargs):
        self.base = base
        self.stripe_id = stripe_id
        self.rotate_size = rotate_size
        self.rotate_index = 0
        self.file = None

    def open(self):
        self.rotate_index += 1
        self.written = 0

        name = str(int(round(time() * 1000)))
        self.name = '{}_{}'.format(name, self.rotate_index)
        # build scheme: /base/<stripe_id>/<last_name_letter>/<last_2_name_letters>/name_with_rotate_index
        self.path = os.path.join(self.base, self.stripe_id, name[-1:], name[-3:-1], self.name)
        os.makedirs(os.path.dirname(self.path))

        self.file = open(self.path, 'a', buffering=0)

    def close(self):
        if self.file:
            self.path = None
            self.name = None
            self.file.close()
            self.file = None

    def write(self, data):
        if not self.file:
            self.open()
        self.file.write(data)
        self.written += len(data)
        # rotate, if exceed size
        if self.rotate_size and self.written >= self.rotate_size:
            self.open()