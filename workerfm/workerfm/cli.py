# -*- coding: utf-8 -*-

import argparse
from ConfigParser import ConfigParser
from gevent.monkey import patch_all
patch_all()
from .worker import Worker
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
    loglevel = logging.ERROR
    if args.loginfo:
        loglevel = logging.INFO
    if args.logdebug:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel, format='%(levelname)s\t%(asctime)s\t %(message)s')

    worker = Worker(endpoint=dict(config.items('endpoint')),
                    maxjobs=config.getint('worker', 'maxjobs'))
    worker.run()

