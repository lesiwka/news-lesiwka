from flask import Flask

from routes.index import index
from routes.refresh import refresh
from routes.stats import stats


def init_app(app: Flask):
    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/_refresh", view_func=refresh)
    app.add_url_rule("/_stats", view_func=stats)
