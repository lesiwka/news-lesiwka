import os
from concurrent import futures
from datetime import datetime, timedelta, timezone

import requests
from flask import Response, redirect, request

from cache import cache
from extractor import Extractor
from utils import validate

GNEWS_API_KEY = os.environ["GNEWS_API_KEY"]
GNEWS_INTERVAL = int(os.getenv("GNEWS_INTERVAL", 900))
EXTRACTOR_API_KEY = os.environ["EXTRACTOR_API_KEY"]
EXTRACTOR_CONCURRENCY_LIMIT = int(os.getenv("EXTRACTOR_CONCURRENCY_LIMIT", 1))


@cache.lock
def refresh():
    response = (
        Response()
        if request.headers.get("X-Appengine-Cron") == "true"
        else redirect("/")
    )

    if not cache.check(interval=GNEWS_INTERVAL):
        return response

    now = datetime.now(tz=timezone.utc)
    old_articles = [
        article
        for article in cache.get() or []
        if now - datetime.fromisoformat(article["publishedAt"]) < timedelta(2)
    ]

    params = dict(
        apikey=GNEWS_API_KEY,
        country="ua",
        category="general",
        lang="uk",
    )
    try:
        news = requests.get(
            "https://gnews.io/api/v4/top-headlines", params=params
        ).json()
    except requests.RequestException:
        return response

    old_urls = [article["url"] for article in old_articles]
    new_articles = [
        article
        for article in news.get("articles", [])
        if validate(article["title"]) and article["url"] not in old_urls
    ]

    articles = (new_articles + old_articles)[:50]

    extractor = Extractor(EXTRACTOR_API_KEY)
    with futures.ThreadPoolExecutor(EXTRACTOR_CONCURRENCY_LIMIT) as executor:
        future_to_article = {
            executor.submit(extractor.extract, article["url"]): article
            for article in articles
            if "content_full" not in article
        }
        for future in futures.as_completed(future_to_article):
            article = future_to_article[future]
            if content_full := future.result():
                article["content_full"] = content_full

    if new_articles or future_to_article:
        cache.avg(len(new_articles))
        cache.put(articles)

    return response
