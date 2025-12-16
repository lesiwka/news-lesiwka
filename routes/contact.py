import os

from flask import make_response, redirect, render_template, request

CONTACT = os.environ["CONTACT"]


def contact():
    # if not request.user_agent.string.startswith("NovynyApp/"):
    #     return redirect("/")

    return make_response(render_template("contact.html", contact=CONTACT))
