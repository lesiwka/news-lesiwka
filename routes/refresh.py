import hashlib
import os
import re
from concurrent import futures
from datetime import datetime

import requests
from dateutil import tz
from flask import Response, redirect, render_template, request

from cache import cache
from extractor import Extractor
from utils import validate

GNEWS_API_KEY = os.environ["GNEWS_API_KEY"]
GNEWS_INTERVAL = int(os.getenv("GNEWS_INTERVAL", 900))
EXTRACTOR_API_KEYS = os.environ["EXTRACTOR_API_KEYS"].split(",")
EXTRACTOR_CONCURRENCY_LIMIT = int(os.getenv("EXTRACTOR_CONCURRENCY_LIMIT", 1))
TZ = tz.gettz("Europe/Kiev")


def _render(articles):
    for article in articles:
        article_hash = hashlib.shake_256(article["url"].encode())
        article["id"] = "article-" + article_hash.hexdigest(4)

        if validate(desc := article["description"]) and not desc.startswith(
            (title := article["title"])[: len(title) // 2]
        ):
            content = article.get("content_full", article["content"])
            pattern = re.escape(content[: len(desc) // 4]) + r".*"
            article["description"] = re.sub(pattern, "", desc).rstrip(" .")
        else:
            article["description"] = ""

        article["content"] = re.sub(r"\[\d+ chars]$", "", article["content"])
        if "content_full" in article:
            article["content_full"] = re.sub(
                r"^("
                r"|Якщо.*?помилку.*?виділіть.*?натисніть\s+Ctrl\+Enter.*?"
                r"|Будь\s+ласка,\s+читайте\s+текст\s+після\s+реклами"
                r"|.*?використ\w+?\s+файл\w*?\s+cookie.*"
                r")$",
                "",
                article["content_full"],
                flags=re.MULTILINE,
            )

        pub = datetime.fromisoformat(article["publishedAt"]).astimezone(TZ)
        article["published"] = (
            f"{pub.day}.{pub.month:02}.{pub.year:04}, "
            f"{pub.hour}:{pub.minute:02}"
        )

        article["source_domain"] = article["source"]["url"].split("://")[-1]

    return render_template("index.html", articles=articles)


@cache.lock
def refresh():
    response = (
        Response()
        if request.headers.get("X-Appengine-Cron") == "true"
        else redirect("/")
    )

    if not cache.check(interval=GNEWS_INTERVAL):
        return response

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

    old_articles = cache.get()

    old_urls = {article["url"] for article in old_articles}
    new_articles = [
        article
        for article in news.get("articles", [])
        if validate(article["title"])
        and article["url"] not in old_urls
        and not re.search(
            r"(астролог|гороскоп|знак.+?зодіак)",
            article["title"],
            flags=re.IGNORECASE,
        )
    ]

    articles = (new_articles + old_articles)[:50]

    extractor = Extractor(EXTRACTOR_API_KEYS)
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

    if new_articles or future_to_article or not cache.page():
        cache.put(articles, _render)

    return response
