#!/usr/bin/env python
# -*- coding: utf-8 -*-

class RadioError(Exception):
    pass


class TooManyRedirects(RadioError):
    pass


class UnexpectedEnd(RadioError):
    pass


class InvalidContentType(RadioError):
    pass


class InvalidMetaint(RadioError):
    pass


class HttpError(RadioError):
    pass


class ConnectionError(RadioError):
    pass

class ReadError(RadioError):
    pass