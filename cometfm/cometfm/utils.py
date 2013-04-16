#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time

# Exception to activate retries
class RetryException(Exception):
    pass

def call_and_ignore_exceptions(types, fxn, *args, **kwargs):
    try:
        return fxn(*args, **kwargs)
    except Exception, exc:
        if any((isinstance(exc, exc_type) for exc_type in types)):
            raise RetryException()
        else:
            raise exc  # raise up unknown error

def retry_on_exceptions(types, tries=2, delay=1):
    def decorator(fxn):
        def f_retry(*args, **kwargs):
            local_tries = tries  # make mutable
            while local_tries > 1:
                try:
                    return call_and_ignore_exceptions(types, fxn, *args, **kwargs)
                except RetryException:
                    local_tries -= 1
                    if delay:
                        logging.debug("Waiting %s seconds to retry %s..." % (delay, fxn.__name__))
                        if delay:
                            time.sleep(delay)
                    logging.debug("Retrying function %s" % fxn.__name__)
            logging.debug("Last try... and I will raise up whatever exception is raised")
            return fxn(*args, **kwargs)
        return f_retry
    return decorator