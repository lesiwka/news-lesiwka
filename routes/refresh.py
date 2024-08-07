import hashlib
import logging
import os
import re
from concurrent import futures
from datetime import datetime

import requests
from dateutil import tz
from flask import Response, redirect, render_template, request

from cache import cache
from extractor import Extractor
from routes import START_TIME
from utils import validate

GNEWS_API_KEY = os.environ["GNEWS_API_KEY"]
GNEWS_INTERVAL = int(os.getenv("GNEWS_INTERVAL", 900))
EXTRACTOR_API_KEYS = os.environ["EXTRACTOR_API_KEYS"].split(",")
EXTRACTOR_CONCURRENCY_LIMIT = int(os.getenv("EXTRACTOR_CONCURRENCY_LIMIT", 1))
TZ = tz.gettz("Europe/Kiev")

logger = logging.getLogger(__name__)


def _render(articles):
    for article in articles:
        article_hash = hashlib.shake_256(article["url"].encode())
        article["id"] = "article-" + article_hash.hexdigest(4)

        article["content"] = re.sub(r"\[\d+ chars]$", "", article["content"])
        if content := article.get("content_full"):
            content = re.sub(
                r"^("
                r"|Якщо.*?помилку.*?виділіть.*?натисніть\s+Ctrl\+Enter.*?"
                r"|Будь\s+ласка,\s+читайте\s+текст\s+після\s+реклами"
                r"|.*?використ\w+?\s+файл\w*?\s+cookie.*"
                r"|https?://\S+"
                r"|(.+)(\n+\2)+"
                r")(?:\n|$)",
                "",
                content.strip(),
                flags=re.MULTILINE,
            )

            semititle = (title := article["title"])[: len(title) // 2]
            if validate(
                desc := article["description"]
            ) and not desc.startswith(semititle):
                pat = re.escape(content[: len(desc) // 4]) + r".*"
                desc = re.sub(pat, "", desc).rstrip(" .")
            else:
                desc = ""

            if not article["description"]:
                pat = re.compile(r".+?(?:[^.]|\.\.\.)$", flags=re.MULTILINE)
                if match := pat.match(content):
                    desc = match.group(0)
                    content = pat.sub("", content)
                if desc.startswith(semititle):
                    desc = ""

            if not desc and content.count("\n") > 0:
                desc_, content_ = content.split("\n", maxsplit=1)
                desc_ = desc_.rstrip(" .")
                if len(desc_) > 300:
                    pat = re.compile(r"\.\s")
                    if pat.search(desc_):
                        desc_, _ = pat.split(desc_, maxsplit=1)
                    else:
                        desc_ = ""
                    content_ = content
                if len(content_) > len(desc_):
                    desc, content = desc_, content_

            if desc == title and article["description"]:
                desc = article["description"]

            article["content_full"] = content
            article["description"] = desc

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

    old_articles = cache.get()

    if cache.upd() < START_TIME:
        cache.put(old_articles, _render)
        return response

    if not cache.check(interval=GNEWS_INTERVAL):
        return response

    params = dict(
        apikey=GNEWS_API_KEY,
        country="ua",
        category="general",
        lang="uk",
    )
    try:
        res = requests.get(
            "https://gnews.io/api/v4/top-headlines", params=params
        )
    except requests.RequestException as e:
        logger.error("News fetching failure: %s", e)
        return response

    if res.status_code != 200:
        logger.error("News fetching error: %s %s", res.status_code, res.text)
        return response

    news = res.json()

    old_urls = {article["url"] for article in old_articles}
    new_articles = [
        article
        for article in news.get("articles", [])
        if validate(article["title"])
        and article["url"] not in old_urls
        and not any(
            re.search(
                r"("
                r"астролог|гороскоп|знак.+?зодіак|езотери[кч]"
                r"|"
                r"hamster\s+kombat|хамстер"
                r")",
                article.get(section, ""),
                flags=re.IGNORECASE,
            )
            for section in ("title", "description")
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
