import hashlib
import http
import re
from datetime import datetime, timezone

from dateutil import tz
from flask import Response, make_response, render_template, request

from cache import cache

START_TIME = datetime.now(tz=timezone.utc).replace(microsecond=0)
TZ = tz.gettz("Europe/Kiev")


def index():
    mtime = START_TIME
    since = request.if_modified_since

    if upd := cache.upd():
        mtime = max(mtime, datetime.fromtimestamp(upd, tz=timezone.utc))
        if since and mtime <= since:
            return Response(status=http.HTTPStatus.NOT_MODIFIED)

        articles = cache.get()
    else:
        articles = []

    if not articles:
        if since and mtime <= since:
            return Response(status=http.HTTPStatus.NOT_MODIFIED)

        response = make_response(render_template("loading.html"))
        response.last_modified = mtime
        return response

    for article in articles:
        article_hash = hashlib.shake_256(article["url"].encode())
        article["id"] = "article-" + article_hash.hexdigest(4)

        article["content"] = re.sub(r"\[\d+ chars]$", "", article["content"])

        pub = datetime.fromisoformat(article["publishedAt"]).astimezone(TZ)
        article["published"] = (
            f"{pub.day}.{pub.month:02}.{pub.year:04}, "
            f"{pub.hour}:{pub.minute:02}"
        )

        article["source_domain"] = article["source"]["url"].split("://")[-1]

    response = make_response(render_template("index.html", articles=articles))
    response.last_modified = mtime

    return response
