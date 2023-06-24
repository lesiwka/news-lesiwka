import http
import json
import time

from flask import Response
from google.appengine.api import memcache

from cache import tmpcache
from utils import time_limit

_ts_key = "ts"
_upd_key = "upd"
_data_key = "data"
_page_key = "page"
_lock_key = "lock"
_lock_time = 300


def check(interval):
    multi = memcache.get_multi([_ts_key, _data_key])
    expired = (now := int(time.time())) - (multi.get(_ts_key) or 0) > interval

    if expired or multi.get(_data_key) is None:
        memcache.set(_ts_key, now)
        return True

    return False


def upd():
    return memcache.get(_upd_key)


def get():
    if raw := memcache.get(_data_key):
        return json.loads(raw)

    articles = tmpcache.get()
    memcache.set(_data_key, json.dumps(articles, ensure_ascii=False))
    return articles


def page():
    return memcache.get(_page_key)


def put(articles, renderer):
    while articles and memcache.set_multi(
        {
            _upd_key: int(time.time()),
            _data_key: json.dumps(articles, ensure_ascii=False),
            _page_key: renderer(articles),
        }
    ):
        articles.pop()
    tmpcache.put(articles, renderer=None)


def stats():
    multi = memcache.get_multi([_ts_key, _upd_key, _data_key])
    ts = multi.get(_ts_key)
    upd_ = multi.get(_upd_key)
    raw = multi.get(_data_key)

    try:
        count = len(json.loads(raw))
    except (TypeError, json.JSONDecodeError):
        count = None
    try:
        size = len(raw.encode(errors="replace"))
    except AttributeError:
        size = None

    return dict(ts=ts, upd=upd_, count=count, size=size)


def lock(f):
    def wrapper(*args, **kwargs):
        due = time.time() + _lock_time
        while not memcache.add(_lock_key, int(time.time()), time=_lock_time):
            if time.time() > due:
                return Response(status=http.HTTPStatus.LOCKED)

            time.sleep(0.1)

        try:
            return time_limit(_lock_time, f, *args, **kwargs)
        finally:
            memcache.delete(_lock_key)

    return wrapper
