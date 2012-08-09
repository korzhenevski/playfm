# -*- coding: utf-8 -*-

import argparse
from ConfigParser import ConfigParser
from gevent.monkey import patch_all
patch_all()
from workerfm.worker import Worker
import logging

def main():
    parser = argparse.ArgumentParser(description='Radio platform worker')
    parser.add_argument('config_file', help='config file path')
    parser.add_argument('--loginfo', help='log info messages', action='store_true')
    parser.add_argument('--logdebug', help='log debug messages', action='store_true')

    args = parser.parse_args()

    config = ConfigParser()
    config.read(args.config_file)

    # ajust logger level
    if args.loginfo:
        logging.basicConfig(level=logging.INFO)
    if args.logdebug:
        logging.basicConfig(level=logging.DEBUG)

    worker = Worker(endpoint=dict(config.items('endpoint')),
                    threads=config.getint('threads'))
    worker.run()

