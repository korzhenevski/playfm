from gevent.monkey import patch_all
patch_all()
from .checker import Checker
import pymongo
from rvlib import cli_bootstrap

def main():
    conf = cli_bootstrap(__name__, description='Radio streams checker')
    db = pymongo.Connection(host=conf.get('mongodb', 'host'))[conf.get('mongodb', 'database')]
    checker = Checker(db,
        interval=conf.getint('checker', 'interval'),
        retries=conf.getint('checker', 'retries'),
        threads=conf.getint('checker', 'threads'),
        timeout=conf.getint('checker', 'timeout'))
    checker.run()

