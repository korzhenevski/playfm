from gevent.monkey import patch_all
patch_all()
from .worker import Worker
import pymongo
from rvlib import cli_bootstrap

def main():
    config = cli_bootstrap(__name__, description='Radio streams checker')
    db = pymongo.Connection(host=config.get('mongodb', 'host'))[config.get('mongodb', 'database')]
    worker = Worker(db, check_interval=config.getint('worker', 'check_interval'))
    worker.run()

