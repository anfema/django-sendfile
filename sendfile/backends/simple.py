import os
import stat
import re
try:
    from email.utils import parsedate_tz, mktime_tz
except ImportError:
    from email.Utils import parsedate_tz, mktime_tz

from django.core.files.base import File
from django.http import HttpResponse, HttpResponseNotModified
from django.utils.http import http_date


def sendfile(request, filename, **kwargs):
    # Respect the If-Modified-Since header.
    statobj = os.stat(filename)

    if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'),
                              statobj[stat.ST_MTIME], statobj[stat.ST_SIZE]):
        return HttpResponseNotModified()

    response = None

    # Fullfill range request
    rng = request.META.get('HTTP_RANGE', None)
    if rng and rng.startswith('bytes='):
        # parse range
        rngs = rng[6:].split(",")
        if len(rngs) == 1:
            start = 0
            size = statobj.st_size
            length = size

            # just one range, we can fullfill that
            parts = rngs[0].split("-")
            data = None
            with open(filename, 'rb') as fp:
                if parts[0] == "":
                    # client wants the last x bytes
                    start = length - int(parts[1])
                    length = int(parts[1])
                else:
                    start = int(parts[0])

                if parts[1] == "":
                    # client wants a start offset
                    start = int(parts[1])
                    length -= start
                else:
                    length = int(parts[1]) - start

                fp.seek(start, os.SEEK_SET)
                data = fp.read(length)
            if data:
                response = HttpResponse(data, status=206)
                response["Content-Range"] = "bytes {start}-{end}/{size}".format(start=start, end=start+length, size=size)
                response["Content-Length"] = length

    # no response from a range request, reply with complete file
    if not response:
        with File(open(filename, 'rb')) as f:
            response = HttpResponse(f.chunks())

    response["Last-Modified"] = http_date(statobj[stat.ST_MTIME])
    response["Accept-Ranges"] = "bytes"
    return response


def was_modified_since(header=None, mtime=0, size=0):
    """
    Was something modified since the user last downloaded it?

    header
      This is the value of the If-Modified-Since header.  If this is None,
      I'll just return True.

    mtime
      This is the modification time of the item we're talking about.

    size
      This is the size of the item we're talking about.
    """
    try:
        if header is None:
            raise ValueError
        matches = re.match(r"^([^;]+)(; length=([0-9]+))?$", header,
                           re.IGNORECASE)
        header_date = parsedate_tz(matches.group(1))
        if header_date is None:
            raise ValueError
        header_mtime = mktime_tz(header_date)
        header_len = matches.group(3)
        if header_len and int(header_len) != size:
            raise ValueError
        if mtime > header_mtime:
            raise ValueError
    except (AttributeError, ValueError, OverflowError):
        return True
    return False
