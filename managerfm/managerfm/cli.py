import logging
import argparse
from gevent.monkey import patch_all
patch_all()

import pymongo
from ConfigParser import ConfigParser
from redis import Redis
from managerfm.trackfactory import TrackFactory
from managerfm.server import ManagerServer

def main():
    parser = argparse.ArgumentParser(description='Radio platform manager')
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
