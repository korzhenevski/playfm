from cometfm_pb2 import *
from rv_pb2 import *

def pb_safe_parse(klass, data):
    try:
        return klass.FromString(data)
    # TODO: concretize exceptions
    except Exception:
        return None