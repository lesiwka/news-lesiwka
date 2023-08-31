import itertools
import logging
import random

import requests
from bs4 import BeautifulSoup

from utils import validate

logger = logging.getLogger(__name__)


class Extractor:
    url = "https://extractorapi.com/api/v1/extractor"
    _field = "clean_html"

    def __init__(self, apikeys):
        self._apikeys = itertools.cycle(random.sample(apikeys, len(apikeys)))
        self._session = requests.Session()

    def extract(self, url):
        params = dict(
            apikey=next(self._apikeys),
            fields=self._field,
            url=url,
        )
        try:
            res = self._session.get(self.url, params=params)
        except requests.RequestException as e:
            logger.error("Article extraction failure: %s (%s)", e, url)
            return None

        if res.status_code != 200:
            logger.error(
                "Article extraction error: %s %s (%s)",
                res.status_code,
                res.text,
                url,
            )
            return None

        extracted = res.json()

        if html := extracted.get(self._field):
            bs = BeautifulSoup(html, "html.parser")
            return "\n".join(
                p.text
                for p in bs.select("p")
                if validate(p.text) and "extractorapi" not in p.text.lower()
            )
