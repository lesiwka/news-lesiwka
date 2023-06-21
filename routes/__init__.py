from flask import Flask

from .data import data
from .index import index
from .refresh import refresh
from .stats import stats


def init_app(app: Flask):
    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/_data", view_func=data)
    app.add_url_rule("/_refresh", view_func=refresh)
    app.add_url_rule("/_stats", view_func=stats)
