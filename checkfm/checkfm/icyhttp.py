import httplib
from httplib import LineAndFileWrapper, BadStatusLine

class ShoutcastHTTPResponse(httplib.HTTPResponse):
    def _read_status(self):
        # Initialize with Simple-Response defaults
        line = self.fp.readline()
        if self.debuglevel > 0:
            print "reply:", repr(line)
        if not line:
            # Presumably, the server closed the connection before
            # sending a valid response.
            raise BadStatusLine(line)
        try:
            [version, status, reason] = line.split(None, 2)
        except ValueError:
            try:
                [version, status] = line.split(None, 1)
                reason = ""
            except ValueError:
                # empty version will cause next test to fail and status
                # will be treated as 0.9 response.
                version = ""

        """
        Shoutcast "Fancy" HTTP fix
        """
        if version == 'ICY':
            version = 'HTTP/1.0'

        if not version.startswith('HTTP/'):
            if self.strict:
                self.close()
                raise BadStatusLine(line)
            else:
                # assume it's a Simple-Response from an 0.9 server
                self.fp = LineAndFileWrapper(line, self.fp)
                return "HTTP/0.9", 200, ""

        # The status code is a three-digit number
        try:
            status = int(status)
            if status < 100 or status > 999:
                raise BadStatusLine(line)
        except ValueError:
            raise BadStatusLine(line)
        return version, status, reason

httplib.HTTPConnection.response_class = ShoutcastHTTPResponse
