from flask import request

from cache import cache


def stats():
    return (
        f"<title>{request.path}</title>\n"
        "<pre>\n"
        + "\n".join(f"{k}: {v}" for k, v in cache.stats().items())
        + "\n</pre>\n"
    )
