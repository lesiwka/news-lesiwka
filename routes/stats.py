from flask import render_template

from cache import cache


def stats():
    return render_template("stats.html", stats=cache.stats())
