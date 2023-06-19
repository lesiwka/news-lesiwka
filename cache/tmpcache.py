import json
import tempfile
import time
from pathlib import Path


_path = Path(tempfile.gettempdir()) / "articles.json"
_lock = Path(tempfile.gettempdir()) / "lock.txt"


def check(interval):
    return _path.exists() and time.time() - _path.stat().st_mtime > interval


def upd():
    if _path.exists():
        return int(_path.stat().st_mtime)


def get():
    if raw := _path.read_text():
        return json.loads(raw)
    return []


def put(data):
    tmp = _path.with_stem(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False))
    tmp.replace(_path)


def stats():
    try:
        st = _path.stat()
    except FileNotFoundError:
        return dict(ts=None, upd=None, count=None, size=None, avg=None)

    try:
        data_len = len(json.loads(_path.read_text()))
    except (TypeError, json.JSONDecodeError):
        data_len = None

    mtime = int(st.st_mtime)
    return dict(
        ts=mtime,
        upd=mtime,
        count=data_len,
        size=st.st_size,
        avg=None,
    )


def lock(f):
    return f


def avg(diff):
    pass
