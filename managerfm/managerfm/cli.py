from gevent.monkey import patch_all
patch_all()

import logging
import argparse
import pymongo
from ConfigParser import ConfigParser
from redis import Redis
from .trackfactory import TrackFactory
from .server import ManagerServer

def main():
    parser = argparse.ArgumentParser(description='Radio platform manager')
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
    redis = Redis(host=config.get('redis', 'host'), db=config.getint('redis', 'database'))
    track_factory = TrackFactory(
        lastfm_url=config.get('lastfm_api', 'url'),
        lastfm_api_key=config.get('lastfm_api', 'key')
    )

    server = ManagerServer(
        endpoint_config=dict(config.items('endpoint')),
        track_factory=track_factory, redis=redis, db=db
    )
    server.run()

if __name__ == '__main__':
    main()
