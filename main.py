import lesiwka
from flask import Flask
from flask_bootstrap import Bootstrap5
from google.appengine.api import wrap_wsgi_app

import routes

app = Flask(__name__)
app.json.ensure_ascii = False
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)

Bootstrap5(app)
app.config["BOOTSTRAP_BOOTSWATCH_THEME"] = "sandstone"

app.jinja_env.filters["lesiwka"] = lesiwka.encode

routes.init_app(app)
