import http
import json
import time
from datetime import datetime

from flask import Response
from google.appengine.api import memcache

from utils import time_limit

_ts_key = "ts"
_data_key = "data"
_lock_key = "lock"
_lock_time = 300
_count_avg = "count_avg"
_count_cur = "count_cur"


def ts():
    return memcache.get(_ts_key)


def get():
    if raw := memcache.get(_data_key):
        return json.loads(raw)
    return []


def put(data):
    while data and memcache.set_multi(
        {
            _ts_key: int(time.time()),
            _data_key: json.dumps(data, ensure_ascii=False),
        }
    ):
        data.pop()


def stats():
    multi = memcache.get_multi([_ts_key, _data_key, _count_avg, _count_cur])
    ts_ = multi.get(_ts_key)
    raw = multi.get(_data_key)
    daily_ = multi.get(_count_avg, multi.get(_count_cur))

    try:
        count = len(json.loads(raw))
    except (TypeError, json.JSONDecodeError):
        count = None
    try:
        size = len(raw.encode(errors="replace"))
    except AttributeError:
        size = None

    return dict(ts=ts_, count=count, size=size, daily=daily_)


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


def daily(diff):
    memcache.incr(_count_cur, diff, initial_value=0)

    multi = memcache.get_multi([_count_avg, _count_cur])

    now = datetime.now()
    if now.hour == now.minute == 0:
        cur = multi[_count_cur]
        avg = multi.get(_count_avg, -cur) or cur
        memcache.set_multi({_count_avg: (avg + cur) // 2, _count_cur: 0})
