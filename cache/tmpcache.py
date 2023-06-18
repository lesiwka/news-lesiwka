import json
import tempfile
from pathlib import Path


_path = Path(tempfile.gettempdir()) / "articles.json"
_lock = Path(tempfile.gettempdir()) / "lock.txt"


def ts():
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
        return dict(ts=None, count=None, size=None, daily=None)

    try:
        data_len = len(json.loads(_path.read_text()))
    except (TypeError, json.JSONDecodeError):
        data_len = None

    return dict(
        cache_ts=int(st.st_mtime),
        cache_count=data_len,
        cache_size=st.st_size,
        daily=None,
    )


def lock(f):
    return f


def daily(diff):
    pass
