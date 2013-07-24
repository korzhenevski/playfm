#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import time
from zlib import crc32


def get_ts():
    """ get rounded int timestamp """
    return int(time())


def fasthash(data):
    data = unicode(data, 'utf-8', 'ignore')
    """ unsigned crc32 """
    return unicode(crc32(data) & 0xffffffff)


def parse_stream_title(rawmeta):
    """ extract stream title from shoutcast meta """
    try:
        # add chardet
        rawmeta = rawmeta.decode('utf8', 'ignore')
        meta = dict([chunk.split('=', 1) for chunk in rawmeta.split(';') if '=' in chunk])
        meta = dict([(k.lower(), unicode(v).strip("'\"").strip()) for k, v in meta.iteritems()])
        return meta.get('streamtitle')
    except UnicodeDecodeError:
        return
