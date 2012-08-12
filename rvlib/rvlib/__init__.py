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