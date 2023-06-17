import concurrent
import hashlib
import http
import json
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import lesiwka
import requests
from bs4 import BeautifulSoup
from dateutil.parser import isoparse
from dateutil.tz import gettz
from flask import (
    Flask,
    Response,
    make_response,
    redirect,
    render_template,
    request,
)
from flask_bootstrap import Bootstrap5
from google.appengine.api import memcache, wrap_wsgi_app

app = Flask(__name__)
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)
app.jinja_env.filters["lesiwka"] = lesiwka.encode
app.config["BOOTSTRAP_BOOTSWATCH_THEME"] = "sandstone"

bootstrap = Bootstrap5(app)

GNEWS_API_KEY = os.environ["GNEWS_API_KEY"]
GNEWS_INTERVAL = int(os.getenv("GNEWS_INTERVAL", 900))
EXTRACTOR_API_KEY = os.environ["EXTRACTOR_API_KEY"]
EXTRACTOR_CONCURRENCY_LIMIT = int(os.getenv("EXTRACTOR_CONCURRENCY_LIMIT", 1))

START_TIME = datetime.now(tz=timezone.utc).replace(microsecond=0)
TZ = gettz("Europe/Kiev")


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


class Cache:
    if os.getenv("SERVER_SOFTWARE"):
        _ts_key = "ts"
        _data_key = "data"

        @classmethod
        def ts(cls):
            return memcache.get(cls._ts_key)

        @classmethod
        def get(cls):
            if raw := memcache.get(cls._data_key):
                return json.loads(raw)
            return []

        @classmethod
        def set(cls, data):
            while data and memcache.set_multi(
                {
                    cls._ts_key: int(time.time()),
                    cls._data_key: json.dumps(data, ensure_ascii=False),
                }
            ):
                data.pop()

        @classmethod
        def stats(cls):
            multi = memcache.get_multi([cls._ts_key, cls._data_key])
            ts = multi.get(cls._ts_key)
            raw = multi.get(cls._data_key)

            try:
                count = len(json.loads(raw))
            except (TypeError, json.JSONDecodeError):
                count = None
            try:
                size = len(raw.encode(errors="replace"))
            except AttributeError:
                size = None

            return dict(ts=ts, count=count, size=size)

        @staticmethod
        def lock():
            return memcache.add("lock", int(time.time()), 300)

    else:
        _path = Path(tempfile.gettempdir()) / "articles.json"
        _lock = Path(tempfile.gettempdir()) / "lock.txt"

        @classmethod
        def ts(cls):
            if cls._path.exists():
                return int(cls._path.stat().st_mtime)

        @classmethod
        def get(cls):
            if raw := cls._path.read_text():
                return json.loads(raw)
            return []

        @classmethod
        def set(cls, data):
            tmp = cls._path.with_stem(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False))
            tmp.replace(cls._path)

        @classmethod
        def stats(cls):
            try:
                st = cls._path.stat()
            except FileNotFoundError:
                return dict(ts=None, count=None, size=None)

            try:
                data_len = len(json.loads(cls._path.read_text()))
            except (TypeError, json.JSONDecodeError):
                data_len = None

            return dict(ts=int(st.st_mtime), count=data_len, size=st.st_size)

        @staticmethod
        def lock():
            return True


@app.route("/_refresh")
def refresh():
    response = (
        Response()
        if request.headers.get("X-Appengine-Cron") == "true"
        else redirect("/")
    )

    if not Cache.lock():
        return response

    if ts := Cache.ts():
        if (time.time() - ts) < GNEWS_INTERVAL:
            return response
        old_articles = Cache.get()
    else:
        old_articles = []

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
        return response

    new_articles = [
        article
        for article in news.get("articles", [])
        if validate(article["title"])
        and not next(
            (a for a in old_articles if a["url"] == article["url"]), False
        )
    ]

    if not new_articles:
        return response

    articles = (new_articles + old_articles)[:100]

    extractor = Extractor(EXTRACTOR_API_KEY)
    with ThreadPoolExecutor(EXTRACTOR_CONCURRENCY_LIMIT) as executor:
        future_to_article = {
            executor.submit(extractor.extract, article["url"]): article
            for article in articles
            if "content_full" not in article
        }
        for future in concurrent.futures.as_completed(future_to_article):
            article = future_to_article[future]
            if content_full := future.result():
                article["content_full"] = content_full

    Cache.set(articles)

    return response


@app.route("/")
def index():
    mtime = START_TIME
    since = request.if_modified_since

    if ts := Cache.ts():
        mtime = max(mtime, datetime.fromtimestamp(ts, tz=timezone.utc))
        if since and mtime <= since:
            return Response(status=http.HTTPStatus.NOT_MODIFIED)

        articles = Cache.get()
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

        pub = isoparse(article["publishedAt"]).astimezone(TZ)
        article["published"] = (
            f"{pub.day}.{pub.month:02}.{pub.year:04}, "
            f"{pub.hour}:{pub.minute:02}"
        )

        article["source_domain"] = article["source"]["url"].split("://")[-1]

    response = make_response(render_template("index.html", articles=articles))
    response.last_modified = mtime

    return response


@app.route("/_stats")
def stats():
    return (
        "<pre>\n"
        + "\n".join(f"{k}: {v}" for k, v in Cache.stats().items())
        + "\n</pre>\n"
    )
