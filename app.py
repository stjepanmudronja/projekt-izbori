"""Projekt Izbori analytics site: run with `python app.py` (port 5001).

The code lives in the `webapp/` package, one module per area (see
webapp/__init__.py and CLAUDE.md). Importing the area modules registers
their routes on the one Flask app in webapp/core.py; this file only does
that and starts the server.
"""
import os
import threading

from webapp.core import app, db  # noqa: F401  (`from app import app, db`)
from webapp import (  # noqa: F401  (importing registers each area's routes)
    pages, people, places, home, municipality_map, parties,
    national, sabor, sabor_history, lokalni, turnout, women,
)
from webapp.models import *  # noqa: F401,F403  (models for ad-hoc scripts)
from webapp.pages import SPA_ROUTES  # noqa: F401
from webapp.home import HOME_PUBLIC_FIGURES, _warm_home_cache  # noqa: F401


if __name__ == '__main__':
    # Under the debug reloader only the child process serves requests.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        threading.Thread(target=_warm_home_cache, daemon=True).start()
    app.run(debug=True, port=5001)
