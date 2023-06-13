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


def extract(url):
    params = dict(
        apikey=EXTRACTOR_API_KEY,
        url=url,
        fields="clean_html",
    )
    try:
        extracted_response = requests.get(
            "https://extractorapi.com/api/v1/extractor/", params=params
        )
        extracted = extracted_response.json()
    except Exception:
        extracted = {}

    if html := extracted.get("clean_html"):
        bs = BeautifulSoup(html, "html.parser")
        return "\n".join(
            p.text
            for p in bs.select("p")
            if "extractorapi" not in p.text.lower()
        )


@app.route("/refresh")
def refresh():
    response = (
        Response()
        if request.headers.get("X-Appengine-Cron") == "true"
        else redirect("/")
    )

    articles = []

    if CACHE.exists():
        if (time.time() - CACHE.stat().st_mtime) < 1800:
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
        response_news = requests.get(
            "https://gnews.io/api/v4/top-headlines", params=params
        )
        news = response_news.json()
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

    for article in articles:
        if "content_full" not in article and (
            content_full := extract(article["url"])
        ):
            article["content_full"] = content_full

    tmp = CACHE.with_stem(".tmp")
    tmp.write_text(json.dumps(articles))
    tmp.replace(CACHE)

    return response


def validate(text):
    return re.search("[ґєіїҐЄІЇ]", text) or not re.search("[ёўъыэЁЎЪЫЭ]", text)


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
