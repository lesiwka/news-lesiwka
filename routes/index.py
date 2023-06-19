import http
from datetime import datetime, timezone

from flask import Response, make_response, render_template, request

from cache import cache

START_TIME = datetime.now(tz=timezone.utc).replace(microsecond=0)


def index():
    mtime = START_TIME
    since = request.if_modified_since
    page = None

    if upd := cache.upd():
        mtime = max(mtime, datetime.fromtimestamp(upd, tz=timezone.utc))
        if since and mtime <= since:
            return Response(status=http.HTTPStatus.NOT_MODIFIED)

        page = cache.page()

    if page:
        response = make_response(page)
    elif since and mtime <= since:
        return Response(status=http.HTTPStatus.NOT_MODIFIED)
    else:
        response = make_response(render_template("loading.html"))

    response.last_modified = mtime
    return response
