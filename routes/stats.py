from cache import cache


def stats():
    return (
        "<pre>\n"
        + "\n".join(f"{k}: {v}" for k, v in cache.stats().items())
        + "\n</pre>\n"
    )
