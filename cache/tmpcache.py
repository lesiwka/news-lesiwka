import json
import tempfile
import time
from pathlib import Path


_path = Path(tempfile.gettempdir()) / "articles.json"
_page = Path(tempfile.gettempdir()) / "novyny.html"
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


def page():
    if _page.exists():
        return _page.read_text()


def put(articles, renderer):
    tmp = _path.with_stem(".tmp")
    tmp.write_text(json.dumps(articles, ensure_ascii=False))
    tmp.replace(_path)

    tmp = _page.with_stem(".tmp")
    tmp.write_text(renderer(articles))
    tmp.replace(_page)


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
