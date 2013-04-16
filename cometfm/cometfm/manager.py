#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import time
from gevent.event import Event

class Manager(object):
    def __init__(self):
        self.channels = {}

    def get_channel(self, name):
        if name not in self.channels:
            self.channels[name] = Channel(name, manager=self)
        return self.channels.get(name)

    def wakeup_channel(self, name):
        # skip not watching channels
        if name not in self.channels:
            return
        channel = self.get_channel(name)
        channel.set()
        channel.clear()

    def drop_offline_channels(self, deadline=60):
        if not self.channels:
            return
        deadline = time() - deadline
        drop_list = []
        for name, channel in self.channels.iteritems():
            if channel.clients_count == 0 and deadline <= channel.last_online_at:
                drop_list.append(name)
        for name in drop_list:
            self.channels.pop(name)

    def count_clients(self):
        count = 0
        for channel in self.channels.itervalues():
            count += channel.clients_count
        return count


class Channel(Event):
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.last_online_at = time()
        super(Channel, self).__init__()

    def rawlink(self, *args, **kwargs):
        self.last_online_at = time()
        super(Channel, self).rawlink(*args, **kwargs)

    @property
    def clients_count(self):
        return len(self._links)


if __name__ == '__main__':
    manager = Manager()
    assert manager.get_channel('chan') == manager.get_channel('chan')
    assert len(manager.channels) == 1

    assert manager.count_clients() == 0

    manager.drop_offline_channels(10)
    assert len(manager.channels) == 0
    print 'ok'
