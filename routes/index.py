import http

from flask import Response, make_response, render_template, request

from cache import cache
from routes import START_TIME


def index():
    since = request.if_modified_since
    mtime = max(START_TIME, cache.upd())

    if since and mtime <= since:
        return Response(status=http.HTTPStatus.NOT_MODIFIED)

    if page := cache.page():
        response = make_response(page)
    elif since and mtime <= since:
        return Response(status=http.HTTPStatus.NOT_MODIFIED)
    else:
        response = make_response(render_template("loading.html"))

    response.last_modified = mtime
    return response
