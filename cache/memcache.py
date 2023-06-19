import http
import json
import math
import time
from datetime import datetime, timedelta

from flask import Response
from google.appengine.api import memcache

from utils import time_limit

_ts_key = "ts"
_upd_key = "upd"
_data_key = "data"
_lock_key = "lock"
_lock_time = 300
_count_avg = "count_avg"
_count_cur = "count_cur"
_count_mark = "count_mark"


def check(interval):
    if (now := int(time.time())) - (memcache.get(_ts_key) or 0) > interval:
        memcache.set(_ts_key, now)
        return True
    return False


def upd():
    return memcache.get(_upd_key)


def get():
    if raw := memcache.get(_data_key):
        return json.loads(raw)
    return []


def put(data):
    while data and memcache.set_multi(
        {
            _upd_key: int(time.time()),
            _data_key: json.dumps(data, ensure_ascii=False),
        }
    ):
        data.pop()


def stats():
    multi = memcache.get_multi(
        [_ts_key, _upd_key, _data_key, _count_avg, _count_cur]
    )
    ts = multi.get(_ts_key)
    upd_ = multi.get(_upd_key)
    raw = multi.get(_data_key)
    avg_ = multi.get(_count_avg) or multi.get(_count_cur)

    try:
        count = len(json.loads(raw))
    except (TypeError, json.JSONDecodeError):
        count = None
    try:
        size = len(raw.encode(errors="replace"))
    except AttributeError:
        size = None

    return dict(ts=ts, upd=upd_, count=count, size=size, avg=avg_)


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


def avg(diff):
    now = datetime.now()

    if memcache.get(_count_cur) is not None:
        memcache.incr(_count_cur, diff)

        multi = memcache.get_multi([_count_avg, _count_cur, _count_mark])
        if multi.get(_count_mark) is None:
            cur = multi[_count_cur]
            avg_ = multi.get(_count_avg, -cur) or cur
            memcache.set_multi({_count_avg: (avg_ + cur) // 2, _count_cur: 0})
    else:
        memcache.set(_count_cur, diff)

    tomorrow = datetime.combine(now.date(), now.min.time()) + timedelta(1)
    timeout = math.ceil((tomorrow - now).total_seconds())
    memcache.set(_count_mark, int(now.timestamp()), time=timeout)
