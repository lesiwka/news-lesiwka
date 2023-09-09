import http

from flask import Response, request, send_file

from cache import cache
from routes import START_TIME


def css():
    since = request.if_modified_since
    mtime = max(START_TIME, cache.upd())

    if since and mtime <= since:
        return Response(status=http.HTTPStatus.NOT_MODIFIED)

    if request.user_agent.string.startswith("NovynyApp/"):
        return send_file("static/app.css")
    return send_file("static/non-app.css")
