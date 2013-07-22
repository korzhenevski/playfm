#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import errno


class Recorder(object):
    def __init__(self, volume):
        self.size = 0
        self.volume = volume
        self.stripe = None

    def write(self, data):
        if not self.stripe:
            return

        self.stripe.write(data)
        self.size += len(data)

    def open(self, name):
        self.size = 0
        self.name = name
        self.path = os.path.join(self.volume, name)
        self._makedir(os.path.dirname(self.path))
        self.stripe = open(self.path, 'a', buffering=0)

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
