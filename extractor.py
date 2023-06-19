import requests
from bs4 import BeautifulSoup

from utils import validate


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
