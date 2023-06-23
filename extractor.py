import itertools
import random

import requests
from bs4 import BeautifulSoup

from utils import validate


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
            extracted = self._session.get(self.url, params=params).json()
        except requests.RequestException:
            return None

        if html := extracted.get(self._field):
            bs = BeautifulSoup(html, "html.parser")
            return "\n".join(
                p.text
                for p in bs.select("p")
                if validate(p.text) and "extractorapi" not in p.text.lower()
            )
