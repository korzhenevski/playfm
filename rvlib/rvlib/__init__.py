from rvlib_pb2 import *
import logging

def pb_safe_parse(klass, data):
    #try:
    return klass.FromString(data)
    # TODO: concretize exceptions
    #except Exception as exc:
    #    logging.debug('rvlib parse error: %s', exc)
    #    return None

def pb_dump(message):
    dump = str(message).strip()
    return dump.replace('\n', ', ')

def cli_bootstrap(pkgname, description):
    import logging
    import pkg_resources
    import argparse
    import sys
    from ConfigParser import ConfigParser

    parser = argparse.ArgumentParser(description=description)
    default_config = pkg_resources.resource_filename(pkgname, '../config.ini')
    parser.add_argument('config_file', help='config file path', nargs='?', default=default_config)
    parser.add_argument('--verbose', help='log debug', action='store_true')
    parser.add_argument('--showconfig', help='show default config', action='store_true')

    args = parser.parse_args()
    if args.showconfig:
        with open(default_config) as fp:
            print fp.read()
        sys.exit()

    config = ConfigParser()
    config.read(args.config_file)

    # ajust logger level
    loglevel = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=loglevel, format='%(levelname)s\t%(asctime)s\t %(message)s')

    return config