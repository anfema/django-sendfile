from __future__ import absolute_import

from django.http import HttpResponse

import os.path
from django.conf import settings

def sendfile(request, filename, **kwargs):
    response = HttpResponse()
    relpath = os.path.relpath(filename, settings.SENDFILE_ROOT)
    response['X-Accel-Redirect'] = os.path.join(settings.SENDFILE_URL, relpath)
    return response
