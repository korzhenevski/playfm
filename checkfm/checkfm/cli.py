import argparse
from ConfigParser import ConfigParser
from gevent.monkey import patch_all
patch_all()
from .worker import Worker
import logging
import pymongo

def main():
    parser = argparse.ArgumentParser(description='Radio streams checker')
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

    db = pymongo.Connection(host=config.get('mongodb', 'host'))[config.get('mongodb', 'database')]

    worker = Worker(db, check_interval=config.getint('worker', 'check_interval'))
    worker.run()

