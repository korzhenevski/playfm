#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import time
from gevent.event import Event


class ChannelManager(object):
    def __init__(self):
        self.channels = {}

    def get(self, name):
        if name not in self.channels:
            self.channels[name] = Channel()
        return self.channels.get(name)

    def wait_for_update(self, name, timeout):
        channel = self.get(name)
        channel.wait(timeout)
        return channel

    def update(self, name):
        # skip not exists channel
        if name not in self.channels:
            return
        channel = self.get(name)
        channel.set()
        channel.clear()

    def housekeep(self, deadline=10):
        if not self.channels:
            return
        deadline = time() - deadline
        drop_list = []
        for name, channel in self.channels.iteritems():
            if channel.listeners == 0 and channel.ts <= deadline:
                drop_list.append(name)
        for name in drop_list:
            self.channels.pop(name)

    def get_stats(self, min_listeners=None):
        stats = {}
        for name, channel in self.channels.iteritems():
            if min_listeners is not None and channel.listeners < min_listeners:
                continue
            stats[name] = channel.listeners
        return stats


class Channel(Event):
    def __init__(self):
        self.ts = time()
        super(Channel, self).__init__()

    def rawlink(self, *args, **kwargs):
        self.ts = time()
        super(Channel, self).rawlink(*args, **kwargs)

    @property
    def listeners(self):
        return len(self._links)


if __name__ == '__main__':
    manager = ChannelManager()
    assert manager.get('chan') == manager.get('chan')
    assert len(manager.channels) == 1

    manager.housekeep(-10)
    assert len(manager.channels) == 0
    print 'ok'
