import hashlib
import http
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import humanize
import lesiwka
import requests
from bs4 import BeautifulSoup
from dateutil.parser import isoparse
from flask import (
    Flask,
    Response,
    make_response,
    redirect,
    render_template,
    request,
)
from flask_bootstrap import Bootstrap5

app = Flask(__name__)
app.jinja_env.filters["lesiwka"] = lesiwka.encode
app.config["BOOTSTRAP_BOOTSWATCH_THEME"] = "sandstone"

bootstrap = Bootstrap5(app)

CACHE = Path(tempfile.gettempdir()) / "articles.json"

GNEWS_API_KEY = os.environ["GNEWS_API_KEY"]
EXTRACTOR_API_KEY = os.environ["EXTRACTOR_API_KEY"]


class Extractor:
    url = "https://extractorapi.com/api/v1/extractor"
    _field = "clean_html"

    def __init__(self, apikey):
        self._apikey = apikey
        self._session = requests.Session()

    def extract(self, url):
        params = dict(
            apikey=self._apikey,
            fields=self._field,
            url=url,
        )
        try:
            r = self._session.get(self.url, params=params)
            extracted = r.json()
        except Exception:
            return None

        if html := extracted.get(self._field):
            bs = BeautifulSoup(html, "html.parser")
            return "\n".join(
                p.text
                for p in bs.select("p")
                if "extractorapi" not in p.text.lower()
            )


def validate(text):
    return re.search("[ґєіїҐЄІЇ]", text) or not re.search("[ёўъыэЁЎЪЫЭ]", text)


@app.route("/refresh")
def refresh():
    response = (
        Response()
        if request.headers.get("X-Appengine-Cron") == "true"
        else redirect("/")
    )

    articles = []

    if CACHE.exists():
        if (time.time() - CACHE.stat().st_mtime) < 900:  # 15 minutes
            return response
        if data := CACHE.read_text():
            articles = json.loads(data)

    params = dict(
        apikey=GNEWS_API_KEY,
        country="ua",
        category="general",
        lang="uk",
    )
    try:
        r = requests.get(
            "https://gnews.io/api/v4/top-headlines", params=params
        )
        news = r.json()
    except Exception:
        news = {}

    if new_articles := news.get("articles"):
        for article in reversed(new_articles):
            if not validate(article["title"]):
                continue

            if next((a for a in articles if a["url"] == article["url"]), None):
                continue

            articles.insert(0, article)

    articles = articles[:100]

    extractor = Extractor(EXTRACTOR_API_KEY)
    for article in articles:
        if "content_full" not in article and (
            content_full := extractor.extract(article["url"])
        ):
            article["content_full"] = content_full

    tmp = CACHE.with_stem(".tmp")
    tmp.write_text(json.dumps(articles))
    tmp.replace(CACHE)

    return response


@app.route("/")
def index():
    articles = []
    mtime = None

    if CACHE.exists():
        mtime = int(CACHE.stat().st_mtime)
        since = request.if_modified_since
        if since and mtime <= since.timestamp():
            return Response(status=http.HTTPStatus.NOT_MODIFIED)

        if data := CACHE.read_text():
            articles = json.loads(data)

    if not articles:
        since = request.if_modified_since
        if since and since.timestamp() == 0:
            return Response(status=http.HTTPStatus.NOT_MODIFIED)

        response = make_response(render_template("loading.html"))
        response.last_modified = 0
        return response

    now = datetime.now(tz=timezone.utc)
    humanize.i18n.activate("uk_UA", path="locale")

    for article in articles:
        article_hash = hashlib.shake_256(article["url"].encode())
        article["id"] = "article-" + article_hash.hexdigest(4)

        article["content"] = re.sub(r"\[\d+ chars]$", "", article["content"])

        published_at = isoparse(article["publishedAt"])
        article["published"] = humanize.naturaltime(published_at, when=now)

        article["source_domain"] = article["source"]["url"].split("://")[-1]

    response = make_response(render_template("index.html", articles=articles))
    response.last_modified = mtime

    return response
