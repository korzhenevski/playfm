from ConfigParser import ConfigParser
import sys
import pymongo
from redis import Redis
from managerfm.trackfactory import TrackFactory
from managerfm.server import ManagerServer

def main():
    config_file = sys.argv[1]
    config = ConfigParser()
    config.read(config_file)

    db = pymongo.Connection(host=config.get('mongodb', 'host'))[config.get('mongodb', 'database')]
    redis = Redis(host=config.get('redis', 'host'), db=config.getint('redis', 'database'))
    track_factory = TrackFactory(
        lastfm_url=config.get('lastfm_api', 'url'),
        lastfm_api_key=config.get('lastfm_api', 'key')
    )

    server = ManagerServer(
        endpoint_config=config.get('endpoint', vars=True),
        track_factory=track_factory,
        redis=redis,
        db=db
    )
    server.run()

if __name__ == '__main__':
    main()
