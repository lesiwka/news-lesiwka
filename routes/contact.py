import os

from flask import redirect

CONTACT = os.environ["CONTACT"]


def contact():
    return redirect(CONTACT)
