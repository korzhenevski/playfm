from gevent.monkey import patch_all
patch_all()

import pymongo
from redis import Redis
from rvlib import cli_bootstrap
from .trackfactory import TrackFactory
from .server import ManagerServer

def main():
    config = cli_bootstrap(__name__, description='Radio platform manager')

    db = pymongo.Connection(host=config.get('mongodb', 'host'))[config.get('mongodb', 'database')]
    redis = Redis(host=config.get('redis', 'host'), db=config.getint('redis', 'database'))
    track_factory = TrackFactory(
        lastfm_url=config.get('lastfm_api', 'url'),
        lastfm_api_key=config.get('lastfm_api', 'key')
    )

    server = ManagerServer(
        endpoint_config=dict(config.items('endpoint')),
        track_factory=track_factory, redis=redis, db=db,
        snapshot_file=config.get('server', 'snapshot_file')
    )
    server.run()

if __name__ == '__main__':
    main()
