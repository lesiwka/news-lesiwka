import json
import os
import re
import tempfile
import time
from pathlib import Path

import lesiwka
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template
from flask_bootstrap import Bootstrap5

app = Flask(__name__)
app.jinja_env.filters["lesiwka"] = lesiwka.encode

bootstrap = Bootstrap5(app)

GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
EXTRACTOR_API_KEY = os.getenv("EXTRACTOR_API_KEY")


def extract(url):
    params = dict(
        apikey=EXTRACTOR_API_KEY,
        url=url,
        fields="clean_html",
    )
    extracted_response = requests.get(
        "https://extractorapi.com/api/v1/extractor/", params=params
    )
    extracted = extracted_response.json()

    if html := extracted.get("clean_html"):
        bs = BeautifulSoup(html, "html.parser")
        return "\n".join(
            p.text
            for p in bs.select("p")
            if "extractorapi" not in p.text.lower()
        )


def validate(text):
    return re.search("[ґєіїҐЄІЇ]", text) or not re.search("[ёўъыэЁЎЪЫЭ]", text)


@app.route("/")
def index():
    temp = Path(tempfile.gettempdir()) / "articles.json"
    if not temp.exists() or (time.time() - temp.stat().st_mtime) > 1800:
        params = dict(
            apikey=GNEWS_API_KEY,
            country="ua",
            category="general",
            lang="uk",
        )
        response_news = requests.get(
            "https://gnews.io/api/v4/top-headlines", params=params
        )
        news = response_news.json()

        articles = []
        for article in news["articles"]:
            if not validate(article["title"]):
                continue

            if content_full := extract(article["url"]):
                article["content_full"] = content_full

            articles.append(article)

        temp.write_text(json.dumps(articles))
    else:
        articles = json.loads(temp.read_text())

    return render_template("index.html", articles=articles)
