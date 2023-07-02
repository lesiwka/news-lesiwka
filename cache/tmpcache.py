import json
import tempfile
import time
from pathlib import Path


_path = Path(tempfile.gettempdir()) / "articles.json"
_page = Path(tempfile.gettempdir()) / "index.html"
_lock = Path(tempfile.gettempdir()) / "refresh.lock"


if not _path.exists() and (_init_path := Path(_path.name)).exists():
    _path.write_bytes(_init_path.read_bytes())


def check(interval):
    if _path.exists():
        return time.time() - _path.stat().st_mtime > interval
    return True


def upd():
    if _path.exists():
        return int(_path.stat().st_mtime)


def get():
    if _path.exists() and (raw := _path.read_text()):
        return json.loads(raw)
    return []


def page():
    if _page.exists():
        return _page.read_text()


def put(articles, renderer):
    tmp = _path.with_stem(".tmp")
    tmp.write_text(json.dumps(articles, ensure_ascii=False))
    tmp.replace(_path)

    if renderer:
        tmp = _page.with_stem(".tmp")
        tmp.write_text(renderer(articles))
        tmp.replace(_page)


def stats():
    try:
        st = _path.stat()
    except FileNotFoundError:
        return dict(ts=None, upd=None, count=None, size=None)

    try:
        count = len(json.loads(_path.read_text()))
    except (TypeError, json.JSONDecodeError):
        count = None

    mtime = int(st.st_mtime)
    return dict(ts=mtime, upd=mtime, count=count, size=st.st_size)


def lock(f):
    return f
